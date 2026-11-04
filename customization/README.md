# UI profile adapter (prototype)

Run from rdgen:

    python customization/apply_profile.py --source ../rustdesk --version 1.5.0 --profile customization/example.json --check

Remove --check to apply to CLEAN RustDesk 1.5.0 sources. Reapplying to modified sources intentionally fails. All inputs and source anchors are checked before any writes. Only 1.5.0 is supported; new versions require explicit adaptation and verification.

The example uses purple accent/buttons, text navigation, and 260 logical pixel side panels. Omitted fields preserve upstream behavior. This changes shared Flutter theme/widgets, so mobile/web paths using them also require verification before enabling those build targets.

Integrated into the rdgen form, JSON API, and hosted Windows x64 workflow. Separate local device names are available through device_names: true. Drag resizing is not implemented. The RustDesk sources have not been compiled or visually verified.

Tests (require the sibling rustdesk checkout and git):

    python -m unittest discover -s customization -p test_profile.py

## Integration status
The generator now accepts optional ui_profile JSON through the web form and API, validates supported target/version, and sends it as base64 in the encrypted build configuration. The Windows x64 hosted workflow preserves the adapter before checkout and applies it afterwards. Other targets and self-hosted runners reject enabled profiles. Blank profiles retain the upstream path. Save/load uses the existing form serialization.

No GitHub build has been dispatched; an executable and visual validation are still pending. Device names are implemented in source but not compiled or visually verified.


