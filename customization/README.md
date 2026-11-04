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



## Device name priority
When device_names is enabled, the accessible-device list reads an optional top-level string alias from /api/peers. Display order: nonblank server alias, nonblank local alias, original hostname, ID. The original Peer hostname and ID are preserved; local names are never uploaded. Missing/null/non-string server alias behaves as absent. Server aliases are included in the group cache and are searchable through the existing alias search. Clearing a server alias in a future server response restores the retained local fallback.

The context menu edits only the local fallback and displays a server alias read-only when present. Existing CortenDesk releases that omit alias continue using the local fallback. No CortenDesk changes are made by this client.

The standalone Windows workflow runs three Flutter tests for the display priority before compilation. Runtime/API compatibility with a future CortenDesk response still needs validation once that server support exists.

## Resizable panels
Enable `resizable_panels: true` to let users drag the divider of the accessible-device sidebar and address-book sidebar. The configured widths are initial values. The client saves each panel independently using stable local-option keys, and double-clicking its divider clears the saved preference and restores the configured initial width.

The viewport constrains the displayed width without overwriting a wider saved preference. Portrait layout and profiles with this feature disabled keep the original code path. Windows x86/Sciter is not supported by this Flutter feature.
