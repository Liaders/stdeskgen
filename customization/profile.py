"""Validation shared by the generator and build adapter."""
import json
import re


def validate_profile(raw, version, platform="windows", selfhosted=False):
    if raw in (None, ""):
        return None
    profile = json.loads(raw) if isinstance(raw, str) else raw
    if not isinstance(profile, dict):
        raise ValueError("UI profile must be a JSON object")
    if version != "1.5.0" or platform not in ("windows", "linux", "macos") or selfhosted:
        raise ValueError("UI profiles support RustDesk 1.5.0 on Windows x64, Linux and macOS. Windows x86 uses Sciter and requires a separate UI adapter.")
    allowed = {"schema_version", "accent", "button", "navigation", "group_width", "address_book_width", "device_names"}
    if set(profile) - allowed:
        raise ValueError("Unknown UI profile fields: " + ", ".join(sorted(set(profile) - allowed)))
    if type(profile.get("schema_version")) is not int or profile["schema_version"] != 1:
        raise ValueError("Expected UI profile schema_version 1")
    for key in ("accent", "button"):
        if key in profile and (not isinstance(profile[key], str) or not re.fullmatch(r"#[0-9a-fA-F]{6}", profile[key])):
            raise ValueError(f"{key} must be #RRGGBB")
    for key in ("group_width", "address_book_width"):
        if key in profile and (type(profile[key]) is not int or not 150 <= profile[key] <= 480):
            raise ValueError(f"{key} must be an integer between 150 and 480")
    if profile.get("navigation", "icons") not in ("icons", "text"):
        raise ValueError("navigation must be icons or text")
    if "device_names" in profile and type(profile["device_names"]) is not bool:
        raise ValueError("device_names must be boolean")
    return profile
