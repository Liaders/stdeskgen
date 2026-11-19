"""Compile the actual Windows adapter against WinAPI without building RustDesk."""
import argparse
import json
from pathlib import Path
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args()
root = args.output.resolve()
(root/'src').mkdir(parents=True, exist_ok=True)
(root/'Cargo.toml').write_text('''[package]
name = "statusdesk-cursor-check"
version = "0.1.0"
edition = "2021"
[dependencies]
winapi = { version = "0.3", features = ["winuser"] }
serde_json = "1"
log = "0.4"
''', encoding='utf-8')
module = Path(__file__).with_name('headless_cursor.rs').resolve().as_posix()
(root/'src/lib.rs').write_text('''extern crate self as hbb_common;
pub use log;
pub type ResultType<T> = Result<T, Box<dyn std::error::Error + Send + Sync>>;
pub mod config {
    pub struct Config;
    impl Config {
        pub fn file() -> std::path::PathBuf { std::env::temp_dir().join("statusdesk-cursor-check.toml") }
        pub fn get_option(_: &str) -> String { "N".into() }
    }
}
#[path = '''+json.dumps(module, ensure_ascii=False)+''']
pub mod cursor;
''', encoding='utf-8')
subprocess.run(['cargo', 'test', '--manifest-path', str(root/'Cargo.toml')], check=True)
