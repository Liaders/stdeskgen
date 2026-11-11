use hbb_common::{bail, config, ResultType};
use serde::Deserialize;
use sha2::{Digest, Sha256};
use std::{fs::OpenOptions, io::{Read, Write}, os::windows::fs::OpenOptionsExt, time::Duration, sync::{Mutex, atomic::{AtomicBool, Ordering}}};

const BASE: &str = @BASE@;
const PRODUCT: &str = @PRODUCT@;
const CHANNEL: &str = @CHANNEL@;
const PLATFORM: &str = @PLATFORM@;
const REVISION: u64 = @REVISION@;
const MAX_FILE: u64 = 512 * 1024 * 1024;

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Release {
    schema: u32, product: String, channel: String, revision: u64,
    version: String, app_name: String, platform: String,
    filename: String, size: u64, sha256: String,
}

fn read_bounded(mut reader: impl Read, limit: u64) -> ResultType<Vec<u8>> {
    let mut bytes = Vec::new();
    reader.by_ref().take(limit + 1).read_to_end(&mut bytes)?;
    if bytes.len() as u64 > limit { bail!("Update response exceeds limit"); }
    Ok(bytes)
}

lazy_static::lazy_static! {
    static ref STATUS: Mutex<String> = Mutex::new(serde_json::json!({"status":"idle"}).to_string());
}
static RUNNING: AtomicBool = AtomicBool::new(false);
struct Running;
impl Drop for Running {
    fn drop(&mut self) { RUNNING.store(false, Ordering::Release); }
}
fn begin() -> ResultType<Running> {
    if RUNNING.compare_exchange(false, true, Ordering::AcqRel, Ordering::Acquire).is_err() {
        bail!("An update check is already running");
    }
    Ok(Running)
}
fn status() -> String {
    match STATUS.lock() {
        Ok(value) => value.clone(),
        Err(_) => serde_json::json!({"status":"error","message":"Update status unavailable"}).to_string(),
    }
}
fn set_status(state: &str, version: &str, message: &str) {
    if let Ok(mut value) = STATUS.lock() {
        *value = serde_json::json!({"status":state,"version":version,"message":message}).to_string();
    } else {
        hbb_common::log::warn!("Cannot store update status");
    }
}
pub(crate) fn manual_command(command: &str) -> String {
    if command == "rdgen-update-status" { return status(); }
    let guard = match begin() { Ok(value) => value, Err(_) => return status() };
    let install = command == "rdgen-update-install";
    set_status(if install { "downloading" } else { "checking" }, "", "");
    std::thread::spawn(move || {
        let _guard = guard;
        let result = if install { check_inner(true) } else { probe() };
        if let Err(error) = result {
            hbb_common::log::warn!("Manual StatusDesk update: {}", error);
            set_status("error", "", &error.to_string());
        }
    });
    status()
}
fn ensure_installation() -> ResultType<()> {
    if !crate::platform::is_installed() || !crate::is_server() {
        bail!("Installed StatusDesk service is required");
    }
    if config::is_disable_installation() {
        bail!("Installation is disabled by policy");
    }
    if crate::platform::is_msi_installed()? {
        bail!("StatusDesk EXE updates do not support MSI installations yet");
    }
    Ok(())
}
fn fetch_release() -> ResultType<(reqwest::blocking::Client, Release)> {
    let client = reqwest::blocking::Client::builder()
        .timeout(Duration::from_secs(600))
        .connect_timeout(Duration::from_secs(20))
        .redirect(reqwest::redirect::Policy::none())
        .build()?;
    let url = format!("{}/channels/{}/{}/{}.json", BASE, PRODUCT, CHANNEL, PLATFORM);
    let response = client.get(url).send()?.error_for_status()?;
    let release: Release = serde_json::from_slice(&read_bounded(response, 64 * 1024)?)?;
    if release.schema != 2 || release.product != PRODUCT || release.channel != CHANNEL
        || release.platform != PLATFORM || release.app_name != crate::get_app_name()
        || release.size == 0 || release.size > MAX_FILE
        || release.sha256.len() != 64
        || release.filename != format!("client-{}.exe", PLATFORM)
    { bail!("Update metadata does not match this client"); }
    Ok((client, release))
}
fn probe() -> ResultType<()> {
    ensure_installation()?;
    let (_, release) = fetch_release()?;
    set_status(if release.revision > REVISION { "available" } else { "current" }, &release.version, "");
    Ok(())
}
pub(super) fn check() -> ResultType<()> {
    let _guard = begin()?;
    set_status("checking", "", "");
    let result = check_inner(false);
    if let Err(error) = &result { set_status("error", "", &error.to_string()); }
    result
}
fn check_inner(manually: bool) -> ResultType<()> {
    ensure_installation()?;
    if !super::has_no_active_conns() { bail!("Close active sessions before updating"); }
    let (client, release) = fetch_release()?;
    if release.revision <= REVISION {
        set_status("current", &release.version, "");
        return Ok(());
    }
    set_status("downloading", &release.version, "");
    let download = format!("{}/releases/{}/{}/{}/{}/{}", BASE, PRODUCT, CHANNEL, PLATFORM, release.revision, release.filename);
    let response = client.get(download).send()?.error_for_status()?;
    if response.content_length().map(|n| n != release.size).unwrap_or(false) {
        bail!("Update size mismatch");
    }
    let directory = std::env::temp_dir().join(format!("stdesk-update-{}", uuid::Uuid::new_v4()));
    std::fs::create_dir(&directory)?;
    let path = directory.join(&release.filename);
    let result = (|| -> ResultType<()> {
        let mut output = OpenOptions::new().write(true).create_new(true).share_mode(0).open(&path)?;
        let count = std::io::copy(&mut response.take(release.size + 1), &mut output)?;
        output.flush()?;
        output.sync_all()?;
        drop(output);
        if count != release.size { bail!("Update size mismatch"); }
        // Keep a read-only handle that denies writes/deletion until the installer is launched.
        let mut locked = OpenOptions::new().read(true).share_mode(1).open(&path)?;
        let mut hash = Sha256::new();
        let mut buffer = [0u8; 65536];
        loop {
            let count = locked.read(&mut buffer)?;
            if count == 0 { break; }
            hash.update(&buffer[..count]);
        }
        if hex::encode(hash.finalize()) != release.sha256 {
            bail!("Update SHA-256 mismatch");
        }
        if !super::has_no_active_conns() { bail!("Close active sessions before updating"); }
        if !manually && !config::Config::get_bool_option(base::config::keys::OPTION_ALLOW_AUTO_UPDATE) {
            bail!("Auto update was disabled before installation");
        }
        set_status("installing", &release.version, "");
        @INSTALL_VERIFIED_UPDATE@
        Ok(())
    })();
    if result.is_err() {
        // Remove only our uniquely named staging directory; never touch client configuration.
        let _ = std::fs::remove_file(&path);
        let _ = std::fs::remove_dir(&directory);
    }
    result
}
