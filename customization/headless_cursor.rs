//! Temporary Mouse Keys correction owned by the cursor streaming service.
use hbb_common::{config::Config, log};
use std::{fs::{File, OpenOptions}, io::{Read, Write}, mem, os::windows::fs::OpenOptionsExt, path::PathBuf};
use winapi::um::winuser::{
    GetSystemMetrics, SystemParametersInfoW,
    SM_MOUSEPRESENT, SPI_GETMOUSEKEYS, SPI_SETMOUSEKEYS,
};

// winapi 0.3 omits this Win32 structure and flag.
#[repr(C)]
#[allow(non_snake_case)]
struct MOUSEKEYS {
    cbSize: u32, dwFlags: u32, iMaxSpeed: u32, iTimeToMaxSpeed: u32,
    iCtrlSpeed: u32, dwReserved1: u32, dwReserved2: u32,
}
const MKF_MOUSEKEYSON: u32 = 0x00000001;

fn read() -> std::io::Result<MOUSEKEYS> {
    let mut value: MOUSEKEYS = unsafe { mem::zeroed() };
    value.cbSize = mem::size_of::<MOUSEKEYS>() as _;
    if unsafe { SystemParametersInfoW(SPI_GETMOUSEKEYS, value.cbSize, &mut value as *mut _ as _, 0) } == 0 {
        return Err(std::io::Error::last_os_error());
    }
    Ok(value)
}

fn fields(value: &MOUSEKEYS) -> [u32; 6] {
    [value.dwFlags, value.iMaxSpeed, value.iTimeToMaxSpeed, value.iCtrlSpeed, value.dwReserved1, value.dwReserved2]
}

fn from_fields(v: [u32; 6]) -> MOUSEKEYS {
    MOUSEKEYS { cbSize: mem::size_of::<MOUSEKEYS>() as _, dwFlags: v[0], iMaxSpeed: v[1],
        iTimeToMaxSpeed: v[2], iCtrlSpeed: v[3], dwReserved1: v[4], dwReserved2: v[5] }
}

fn unchanged(current: &MOUSEKEYS, applied: &MOUSEKEYS) -> bool {
    let mut current = fields(current);
    let mut applied = fields(applied);
    // These are runtime button/NumLock states, ignored by SPI_SETMOUSEKEYS.
    current[0] &= !0xb3000000;
    applied[0] &= !0xb3000000;
    current == applied
}

fn write(value: &mut MOUSEKEYS) -> std::io::Result<()> {
    // No SPIF_UPDATEINIFILE: never persist the temporary accessibility setting.
    if unsafe { SystemParametersInfoW(SPI_SETMOUSEKEYS, value.cbSize, value as *mut _ as _, 0) } == 0 {
        return Err(std::io::Error::last_os_error());
    }
    Ok(())
}

fn journal() -> PathBuf { Config::file().with_extension("headless-cursor.json") }

pub fn recover() {
    let path = journal();
    let result = (|| -> hbb_common::ResultType<()> {
        if !path.exists() { return Ok(()); }
        let mut file = match OpenOptions::new().read(true).write(true).share_mode(0).open(&path) {
            Ok(file) => file,
            // Another running StatusDesk process owns this correction.
            Err(error) if error.raw_os_error() == Some(32) => return Ok(()),
            Err(error) => return Err(error.into()),
        };
        let mut bytes = Vec::new();
        file.read_to_end(&mut bytes)?;
        let saved: [[u32; 6]; 2] = serde_json::from_slice(&bytes)?;
        if unchanged(&read()?, &from_fields(saved[1])) { write(&mut from_fields(saved[0]))?; }
        drop(file);
        std::fs::remove_file(&path)?;
        Ok(())
    })();
    if let Err(error) = result { log::warn!("Headless cursor recovery failed: {}", error); }
}

#[derive(Default)]
pub struct Correction {
    attempted: bool,
    journal: Option<File>,
}

impl Correction {
    pub fn update(&mut self, missing_shape: bool) {
        if self.attempted || !missing_shape { return; }
        self.attempted = true;
        if Config::get_option("rdgen-auto-headless-cursor") == "N" || unsafe { GetSystemMetrics(SM_MOUSEPRESENT) } != 0 { return; }
        let result = (|| -> hbb_common::ResultType<()> {
            let original = read()?;
            if original.dwFlags & MKF_MOUSEKEYSON != 0 { return Ok(()); }
            let mut applied = from_fields(fields(&original));
            applied.dwFlags |= MKF_MOUSEKEYSON;
            let saved = [fields(&original), fields(&applied)];
            // Record before changing Windows, so the next process can recover after a crash.
            let mut file = OpenOptions::new().write(true).create_new(true).share_mode(0).open(journal())?;
            file.write_all(&serde_json::to_vec(&saved)?)?;
            file.sync_all()?;
            self.journal = Some(file);
            write(&mut applied)?;
            log::info!("Enabled temporary headless cursor correction");
            Ok(())
        })();
        if let Err(error) = result { log::warn!("Headless cursor correction unavailable: {}", error); }
    }
}

impl Drop for Correction {
    fn drop(&mut self) {
        if self.journal.take().is_some() { recover(); }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn runtime_button_and_numlock_changes_still_allow_restoring_the_temporary_mode() {
        let applied = from_fields([MKF_MOUSEKEYSON | 2, 80, 3000, 3, 0, 0]);
        let current = from_fields([applied.dwFlags | 0x91000000, 80, 3000, 3, 0, 0]);
        assert!(unchanged(&current, &applied));
    }
    #[test]
    fn user_preferences_changed_during_a_session_must_not_be_overwritten() {
        let applied = from_fields([MKF_MOUSEKEYSON | 2, 80, 3000, 3, 0, 0]);
        assert!(!unchanged(&from_fields([2, 80, 3000, 3, 0, 0]), &applied));
        assert!(!unchanged(&from_fields([3, 160, 3000, 3, 0, 0]), &applied));
    }
}
