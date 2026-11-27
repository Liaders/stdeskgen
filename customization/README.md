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
an external **Войти в панель** link to https://desk.status16.ru/login inside the shared
connection frame, to the right of the ID and connection controls. This module is independent of Slim UI
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
The client checkbox initially stays on, including upgrades from clients without
Slim UI: an absent `rdgen-slim-ui-v1` option enables compact mode. An explicit
local `N` keeps the user's manual opt-out across updates; `Y` enables it. The
constructor defaults to including Slim UI, while an explicit build-time false
still omits its code and checkbox. Changes apply immediately.

Slim UI preserves the local-ID/password/logo sidebar and font sizes. It bounds
the remote-ID field to 280 logical pixels, reduces panel padding and list gaps,
and uses a 28-pixel Ready footer at normal text scale. The ID field keeps its natural height; an intrinsic-height row fits the Connect
button to it without enlarging the field. The account stays to the right inside
the original frame in both normal and compact modes, separated by a subtle rule.
The frame and main content have right padding. Grid sizes and action menus are preserved.

`desktop_ui.py` conditionally calls `slim_ui.py`, then stages the independent
account group before the colleagues clone is generated. The account header has its
own small source anchor. The optional Slim UI fingerprint is checked only when
that feature is requested; changed upstream compact layouts fail explicitly.
RustDesk 1.5.0/1.5.1 are checked in CI. A binary/runtime UI check is still needed
after compilation. New bases require compatibility review for enabled adapters.

## Organizations
The desktop UI profile accepts `organizations: true`. The constructor enables
it by default (including old profiles missing this field); an explicit false
keeps it out of the build. The client shows **Организации** with an apartment
icon after the existing tabs. It clones the existing accessible-device view,
with device groups only, an independent search/selection state, and a separate
`rdgen-panel-organizations-width-v1` resize preference. Peer cards use the same
server-authorized peer data and require membership in the returned accessible
device-group list; no user-based fallback is used. No new server API is needed.
Refresh and the group toolbar apply to this tab, and saved five/six-tab orders
and visibility lists are extended to include it, preserving existing visibility
choices by their stable tab indices.
Android and Windows x86/Sciter are unchanged.

Desktop text tab labels are translated down by five logical pixels; icon tabs
retain their original placement. The web-panel action uses a content-sized,
centered text button with ten-pixel horizontal padding; native client login is
preserved when signed out.

## Initial tab order
Clients with Organizations apply this order once on first launch after the update:
Recent sessions, Favorites, Organizations, Colleagues, Discovered, Accessible
devices, Address book. Builds without Colleagues omit that item. Tab indices,
selected-tab identity, and saved visibility are unchanged. The migration writes
the new order and then `rdgen-peer-tab-order-v1-7` (or `-6` without Colleagues).
Later launches use the normal saved user order; the same migration is not applied
again on future updates. A failed write leaves the marker unset for a later retry.

The newer `rdgen-peer-tabs-new-devices-v5` rollout supersedes this initial order
once: Recent sessions, Address book, Favorites, Organizations, Colleagues, New
devices; Discovered and Accessible devices are unchecked. Subsequent launches
and updates preserve the user's changes. Text/icon preference is never reset.
The v5 marker intentionally applies to clients that received the earlier v1/v2/v3/v4
New devices rollouts as well; it is constant across subsequent releases. It
also sets the saved device view to list (`peer-card-ui-type = 2`) once. The
first page render uses list while the asynchronous preferences write completes.
Later changes to either device view or tab layout are preserved.

## New devices (desktop)

The Organizations profile includes a groups-free New devices view over the same
authorized group peers, with identical device cards and organization actions.
It requires `created_at` (ISO 8601 with timezone) in GET `/api/peers`; missing or
invalid dates are excluded rather than inferred from the local first-seen time.
Dates survive the existing account/server-scoped display cache. Devices younger
than 24 hours are always sorted newest first; future dates are excluded.
A lightweight 30-second UI tick refreshes relative ages and expiry without
network requests. A nonzero count and tab label/icon use `#D29922` in both text
and icon navigation modes. Windows x32/Sciter and Android are unchanged.
The selected New devices tab uses `#EAB84B`, a bold count in a rounded bordered
badge with translucent fill, and the native sparkle icon. The zero count is
hidden. Sorting controls are hidden on this fixed-order tab. Tile/grid layouts
reserve a 38px integrated metadata strip with time and organization icons;
at enlarged text scales its contents wrap to two lines. List layout reserves
a separate right region before the original device menu, without changing row
height. Metadata never overlays the native name/ID.

Selecting New devices always refreshes the authorized device snapshot in the
background, even when GroupModel is already initialized. Existing cached rows
remain visible. Ordinary entry retains the twelve-hour dictionary cache; the
manual refresh button still forces dictionary refresh. Concurrent loads share
the existing refresh gate rather than starting duplicate requests.

Successful assignments refresh one device's organization memberships. If that
device is absent from the authorized peers snapshot, refresh peers through the
existing API while retaining the cached dictionaries. Notify peer views and save
the snapshot even when no alias changed. Server implementation/deployment is a
separate task; see `NEW_DEVICES_API_RU.md`.

## ARM64 AppImage archive keys
The AppImage staging script exports the Ubuntu 2012/2018 archive public keys from the runner's installed ubuntu-keyring package, checks their full fingerprints, and replaces all four online keyserver URLs with an ASCII-armored local file URI. ARM64 package signatures are required; suites and payload packages are unchanged. The same packaging script now uses the shared reachable-mirror helper instead of forcing archive.ubuntu.com. CI verifies signed focal ARM64 metadata with the exported keys.

## Desktop organization picker and session panel

With the Organizations desktop profile, `group_refresh.py` adds a shared refresh
gate to `group_model.dart`. Group, user and peer pages contain up to 500 entries.
Concurrent callers await one refresh, and the native device cache is restored
before network loading starts. The cache checks both account token and API server.
Existing rows remain visible during refresh; failed group-dictionary requests
retain the last successful dictionary. A server/account change discards results
from an older request.

Ordinary device refresh reuses the group dictionary for up to twelve hours.
The manual refresh arrow explicitly refreshes dictionaries too. Organizations
use one model owned by GroupModel, instead of creating another loader for each
view. This model keeps its last successful rows on transient network failure;
authentication failures clear them. There is no new server API or idle poller.

Successful alias/binding changes notify the main window through the existing
multi-window channel. It reads that device's work-groups and alias endpoints and
updates the visible memberships/alias, without reloading the full dictionaries.
`desktop_home_page.dart` receives this thin notification hook. The notification
checks the API server and account before touching the main window's data. The
existing `peer_tab_page.dart` refresh callbacks pass the explicit dictionary flag.
Android and Sciter keep their original refresh paths. Test against RustDesk 1.5.1.

`organization_editor.dart` is shared by pre-connection selection, the active
session and the closing reminder. Bound organizations precede the search field;
search suggestions contain only additional candidates. Choosing a bound entry
does not attach it again. New bindings require confirmation, and changing a
confirmed session requires a fresh connection. Organization creation is currently
absent from the client UI. Device aliases can be edited or cleared independently,
using the server's current value and permissions.

The preflight opens this dialog before any organization HTTP request. Its
binding lookup and alias lookup start inside the dialog; catalog loading follows
the binding lookup, using pages of 500. Bound choices become selectable without
waiting for the catalog or alias. A fresh sole binding automatically completes
preflight without requesting the catalog, so this case can briefly show the
dialog. Recent cached catalog names are available for search immediately, but
attaching an unbound choice requires a successful catalog refresh and current
permissions. Closing the dialog prevents late responses from changing its UI or
starting a connection. A changed account/API server cancels the launch intent.
The session and closing-reminder callers likewise refresh aliases inside the
dialog instead of delaying its appearance. These changes are confined to the
existing preflight/editor/API modules and their session callers.

The options catalog is cached in native local options, separately for each API
server, account and device. The first authorized page always refreshes bindings
and permissions. Remaining catalog pages are reused for up to twelve hours if
the total, permissions and first-page contents match. Expiry triggers a full
refresh on next use; there is no idle background polling. Authorization and
conflict responses invalidate this cache. Cached entries never grant access.

Runtime changes to upstream files are limited to existing adapter hooks:
`remote_toolbar.dart` renders themed, 30-pixel control faces and retains the
original chat/record controls; `desktop_home_page.dart` closes the old native
session before creating its replacement so RustDesk cannot reuse that peer's
old transport; the existing launch hook in `multi_window_manager.dart` raises
the main window before showing the organization picker. Translation modules
receive the new labels. No server, Android or Windows x86 changes are required.

Regression checks cover bound/new selection, confirmation, alias prefilling,
catalog reuse/expiry and fresh bindings, native toolbar rendering in both themes,
and preservation of RustDesk's theme extensions. A real reconnection and OS
foreground activation still need verification in the next test client build.

## Desktop list loading — 23 November 2026

The existing desktop `GroupModel` adapter starts the accessible group directory,
users and devices concurrently. Organization memberships refresh independently
of those three lists. Requests retain their existing endpoints, pagination,
authorization and account/server guards; a concurrent success cannot overwrite
an HTTP 401 from another request. Failed required lists do not replace the last
displayed device list. Android and Windows x86 keep their existing paths.

Desktop local option `rdgen-accessible-cache-v1` stores display-only group,
user and device snapshots, including server aliases and memberships in several
organizations. The snapshot must
match both the API server and access token before anything is restored. Cached
rows appear before network refresh, remain visible while it runs, and do not
grant permission to connect or assign an organization. Restoring a snapshot does
not mark it fresh: the first refresh still verifies it with the server. Existing
clients need one successful refresh to populate this new cache. No new
background timer is added.

Startup restoration runs immediately after `_updateLocalUserInfo`, before the
current-user HTTP request completes. The earlier pre-login call from `main.dart`
does not consume the cache's one-shot read. Restoring peers emits the existing
group-load event so already mounted device views update without waiting for
network responses. Native `Group::load()` discards unknown fields (including
the server marker and organization memberships), which is why the desktop
snapshot uses local options instead. Logout clears it. Mobile keeps native
storage. The local options file is readable by the operating-system user, like
the existing organization search cache; passwords are not copied into the snapshot.

Read-only HTTP measurements at page size 500: 967 groups, 6 users, 41 devices
and 20 organizations took about 3.56 seconds sequentially versus 1.62 seconds
concurrently. These are Python HTTP timings, not an end-to-end client benchmark.
The generated client is checked against RustDesk 1.5.1; installed-client timing
and cache display still need a manual check in the next client build.

Regression surface: generated `models/group_model.dart` changes desktop refresh
scheduling and cache storage. `models/user_model.dart` adds a desktop-only
cache-load hook after restoring the local account. Feature modules
`rdgen_organization_data.dart` and `rdgen_organization_catalog.dart` restore that
display snapshot and build fallback memberships in one pass over devices. No
session, transport, server API, or snow-animation code changes are involved.

## Device card refinement

Desktop 1.5.1: New devices, recent sessions, favorites and address books share
organization metadata. Only New devices includes age. Names come from the
existing authorized organization snapshot: one name, Several organizations,
or a confirmed No organization. Unknown memberships remain unlabeled; no
per-card network enumeration or bypass of server visibility is introduced.
Assigned labels are white in dark theme; the building icon follows the label.
At list widths below 680 logical pixels, metadata moves below the native card
and list height reserves 38px. Wider lists keep metadata before the original
menu, leaving name/ID space. Tiles reserve the same integrated bottom strip.

Address-book-only local aliases use native local options scoped to API server,
account ID, address book and device. They never change server aliases or sync
address-book data; clearing the field restores the original visible name. The
entry follows Rename, and the current local alias is prefilled on editing.

Text tabs move up 3px, use a 28px target and rounded hover surface; the active
underline remains. Device tabs activate on primary-button down and dragging
starts only beyond a 10 logical-pixel radial displacement (including diagonal
movement). No preference migration marker is changed by this refinement.

Regression: Python customization tests and
`flutter test ../customization/tab_drag_test.dart` from toolbar_stand.

List metadata no longer wraps below the device at narrow widths. The identity
gets its measured natural name/ID width first; organization uses remaining
space (up to 25 Unicode code points), and time stays full until the organization
reaches its ellipsis/icon minimum. Only then does time shrink. Tooltips retain
full values. List row height remains 45px on all decorated tabs.
