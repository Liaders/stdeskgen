"""Client display/file versions are four-part; Cargo/protocol keep the upstream version."""
import re

SUPPORTED_BASES = ('1.5.0', '1.5.1')


def parts(base, display):
    if base not in SUPPORTED_BASES or not isinstance(display, str) or not re.fullmatch(re.escape(base) + r'\.[1-9][0-9]*', display):
        raise ValueError('Expected client version ' + base + '.<build number>')
    values = tuple(int(x) for x in display.split('.'))
    if any(x > 65535 for x in values):
        raise ValueError('Version components must be between 0 and 65535')
    return values


def revision(base, display):
    major, minor, patch, build = parts(base, display)
    return (major << 48) | (minor << 32) | (patch << 16) | build
