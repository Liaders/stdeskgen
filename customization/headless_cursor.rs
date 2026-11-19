//! Temporary Mouse Keys correction owned by the cursor streaming service.
use hbb_common::{config::Config, log};
use std::{mem, path::PathBuf};
use winapi::um::winuser::{
    GetSystemMetrics, SystemParametersInfoW, MOUSEKEYS, MKF_MOUSEKEYSON,
    SM_MOUSEPRESENT, SPI_GETMOUSEKEYS, SPI_SETMOUSEKEYS,
};

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
        let saved: [[u32; 6]; 2] = serde_json::from_slice(&std::fs::read(&path)?)?;
        if fields(&read()?) == saved[1] { write(&mut from_fields(saved[0]))?; }
        std::fs::remove_file(&path)?;
        Ok(())
    })();
    if let Err(error) = result { log::warn!("Headless cursor recovery failed: {}", error); }
}

#[derive(Default)]
pub struct Correction {
    attempted: bool,
    saved: Option<[[u32; 6]; 2]>,
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
            std::fs::write(journal(), serde_json::to_vec(&saved)?)?;
            self.saved = Some(saved);
            write(&mut applied)?;
            log::info!("Enabled temporary headless cursor correction");
            Ok(())
        })();
        if let Err(error) = result { log::warn!("Headless cursor correction unavailable: {}", error); }
    }
}

impl Drop for Correction {
    fn drop(&mut self) {
        if self.saved.is_some() { recover(); }
    }
}
