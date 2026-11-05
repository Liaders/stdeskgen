use hbb_common::{bail, config, sodiumoxide::crypto::sign, ResultType};
use serde::Deserialize;
use sha2::{Digest, Sha256};
use std::{fs::OpenOptions, io::{Read, Write}, os::windows::fs::OpenOptionsExt, time::{Duration, SystemTime, UNIX_EPOCH}};

const BASE: &str = @BASE@;
const KEY: &str = @KEY@;
const PRODUCT: &str = @PRODUCT@;
const CHANNEL: &str = @CHANNEL@;
const REVISION: u64 = @REVISION@;
const MAX_FILE: u64 = 512 * 1024 * 1024;

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Envelope { payload: String, signature: String }

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Release {
    schema: u32, product: String, channel: String, revision: u64,
    version: String, app_name: String, platform: String,
    filename: String, size: u64, sha256: String, expires: u64,
}

fn read_bounded(mut reader: impl Read, limit: u64) -> ResultType<Vec<u8>> {
    let mut bytes = Vec::new();
    reader.by_ref().take(limit + 1).read_to_end(&mut bytes)?;
    if bytes.len() as u64 > limit { bail!("Update response exceeds limit"); }
    Ok(bytes)
}

pub(super) fn check() -> ResultType<()> {
    if !crate::platform::is_installed() || !crate::is_server() || !super::has_no_active_conns() {
        return Ok(());
    }
    if crate::platform::is_msi_installed()? {
        bail!("Signed StatusDesk EXE updates do not support MSI installations yet");
    }
    let client = reqwest::blocking::Client::builder()
        .timeout(Duration::from_secs(600))
        .connect_timeout(Duration::from_secs(20))
        .redirect(reqwest::redirect::Policy::none())
        .build()?;
    let url = format!("{}/channels/{}/{}/windows-x64.json", BASE, PRODUCT, CHANNEL);
    let response = client.get(url).send()?.error_for_status()?;
    let envelope: Envelope = serde_json::from_slice(&read_bounded(response, 64 * 1024)?)?;
    let key_bytes = hex::decode(KEY)?;
    let Some(key) = sign::PublicKey::from_slice(&key_bytes) else { bail!("Invalid update key"); };
    let signature = sign::Signature::from_bytes(&hex::decode(&envelope.signature)?)?;
    if !sign::verify_detached(&signature, envelope.payload.as_bytes(), &key) {
        bail!("Invalid update signature");
    }
    let release: Release = serde_json::from_str(&envelope.payload)?;
    let now = SystemTime::now().duration_since(UNIX_EPOCH)?.as_secs();
    if release.schema != 1 || release.product != PRODUCT || release.channel != CHANNEL
        || release.platform != "windows-x64" || release.app_name != crate::get_app_name()
        || release.expires <= now || release.size == 0 || release.size > MAX_FILE
        || release.sha256.len() != 64
        || release.filename != "client-windows-x64.exe"
    { bail!("Update metadata does not match this client or has expired"); }
    if release.revision <= REVISION { return Ok(()); }
    let download = format!("{}/releases/{}/{}/{}/{}", BASE, PRODUCT, CHANNEL, release.revision, release.filename);
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
        if !super::has_no_active_conns()
            || !config::Config::get_bool_option(base::config::keys::OPTION_ALLOW_AUTO_UPDATE) {
            return Ok(());
        }
        super::update_new_version(false, &release.version, &path);
        Ok(())
    })();
    if result.is_err() {
        // Remove only our uniquely named staging directory; never touch client configuration.
        let _ = std::fs::remove_file(&path);
        let _ = std::fs::remove_dir(&directory);
    }
    result
}
