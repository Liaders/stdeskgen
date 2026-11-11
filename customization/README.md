# UI profile adapter (prototype)

Run from rdgen:

    python customization/apply_profile.py --source ../rustdesk --version 1.5.0 --profile customization/example.json --check

Remove --check to apply to CLEAN RustDesk 1.5.0 sources. Reapplying to modified sources intentionally fails. All inputs and source anchors are checked before any writes. Only 1.5.0 is supported; new versions require explicit adaptation and verification.

The example uses purple accent/buttons, text navigation, and 260 logical pixel side panels. Omitted fields preserve upstream behavior. This changes shared Flutter theme/widgets, so mobile/web paths using them also require verification before enabling those build targets.

Integrated into the rdgen form, JSON API, and hosted Windows x64 workflow. Separate local device names are available through device_names: true. Drag resizing is available through resizable_panels: true. Its widget tests run before the Windows x64 test build.

Tests (require the sibling rustdesk checkout and git):

    python -m unittest discover -s customization -p test_profile.py

## Integration status
The generator now accepts optional ui_profile JSON through the web form and API, validates supported target/version, and sends it as base64 in the encrypted build configuration. The Windows x64 hosted workflow preserves the adapter before checkout and applies it afterwards. Linux and macOS also support the Flutter profile. Windows x86/Sciter and self-hosted runners reject it. Blank profiles retain the upstream path. Save/load uses the existing form serialization.

Earlier Windows x64, Windows x86, Linux and macOS ARM64 builds completed. The current resizable-panel change is being compiled separately; runtime checks on other OSes are deferred.



## Device name priority
When device_names is enabled, the accessible-device list reads an optional top-level string alias from /api/peers. Display order: nonblank server alias, nonblank local alias, original hostname, ID. The original Peer hostname and ID are preserved; local names are never uploaded. Missing/null/non-string server alias behaves as absent. Server aliases are included in the group cache and are searchable through the existing alias search. Clearing a server alias in a future server response restores the retained local fallback.

The context menu edits only the local fallback and displays a server alias read-only when present. Existing CortenDesk releases that omit alias continue using the local fallback. No CortenDesk changes are made by this client.

The standalone Windows workflow runs three Flutter tests for the display priority before compilation. Runtime/API compatibility with a future CortenDesk response still needs validation once that server support exists.

## Resizable panels
Enable `resizable_panels: true` to let users drag the divider of the accessible-device sidebar and address-book sidebar. The configured widths are initial values. The client saves each panel independently using stable local-option keys, and double-clicking its divider clears the saved preference and restores the configured initial width.

The viewport constrains the displayed width without overwriting a wider saved preference. Portrait layout and profiles with this feature disabled keep the original code path. Windows x86/Sciter is not supported by this Flutter feature.

## Theme-specific main-screen logos
The local constructor shows two PNG logo fields, light and dark, for the image above Your Desktop. Loading an older configuration migrates its common logo into both fields without replacing explicit theme logos. The API still accepts the legacy common logo for backward compatibility. Saved configurations and JSON API use `logolightbase64` / `logodarkbase64`; uploads use `logolightfile` / `logodarkfile`. All images travel in the encrypted build archive. Each missing theme uses the common logo; if only a theme-specific image is supplied, it becomes the fallback too.

Windows x64, Linux, macOS and Android stage all three assets before Flutter builds its manifest. The existing RustDesk 1.5.0/1.5.1 logo widget follows `Theme.of(context).brightness`, including system-theme changes. Windows x86 always uses the light logo, falling back to the common logo; the dark-only logo is ignored on x86. Application icons are unaffected. Changes apply to newly built clients.

## Desktop navigation switch
Desktop UI profiles now include a text/icon tab toggle immediately beside the
view and sorting controls. It uses the existing hover-action style and rounded
18px icons. The profile's navigation value is the initial setting; a local choice
under rdgen-navigation-style-v1 takes precedence after restarting the client.
Text tabs scroll horizontally. Mobile keeps its icon navigation and has no extra
control; the Android adapter opts out explicitly. Windows x86/Sciter is unchanged.
Source compatibility checks cover RustDesk 1.5.0 and 1.5.1. Installed clients need
a new build; a binary/runtime UI check is still required after compilation.

## Desktop account header and optional Slim UI
Windows x64, Linux and macOS clients display the current client account name and
an external **Войти в панель** link to https://desk.status16.ru/login in a shared
row to the right of the connection panel. This module is independent of Slim UI
and does not transfer the client token or perform browser login automatically.
The name uses the existing reactive user model; signed-out clients show
**Вход не выполнен** with a **Войти** button using the existing client
`loginDialog`, just like Accessible devices. The web-panel link is shown only
after client login; the reactive header updates after login/logout.
Android and Windows x86/Sciter are unchanged.

In the constructor, enable **Добавить компактный интерфейс (Slim UI)** under
appearance customization, or set `slim_ui: true` in the UI profile. Only then does
the source staging step include Slim UI and its client checkbox at **Настройки →
Отображение → Интерфейс → Компактный интерфейс (Slim UI)**. Missing or false means
no Slim UI module, hooks, preference reads, translations or checkbox in the client.
Old configurations remain valid and omit this optional feature by default.
The client checkbox initially stays off; its existing local preference persists
under `rdgen-slim-ui-v1` and updates the main screen immediately.

Slim UI preserves the local-ID/password/logo sidebar and font sizes. It bounds
the remote-ID field to 280 logical pixels, reduces panel padding and list gaps,
and uses a 28-pixel Ready footer at normal text scale. Connection controls wrap
inside their own area when needed; the account stays to the right in the shared
row in both normal and compact modes. Grid sizes and action menus are preserved.

`desktop_ui.py` stages the independent account header, then conditionally calls
`slim_ui.py` before the colleagues clone is generated. The account header has its
own small source anchor. The optional Slim UI fingerprint is checked only when
that feature is requested; changed upstream compact layouts fail explicitly.
RustDesk 1.5.0/1.5.1 are checked in CI. A binary/runtime UI check is still needed
after compilation. New bases require compatibility review for enabled adapters.
