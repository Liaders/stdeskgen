# Desktop session organizations

Implemented on the supported RustDesk 1.5.0/1.5.1 desktop preparation paths:
Windows x64, macOS and Linux. Windows x32 is excluded. Android uses the preserved
v1 adapter and assets in `session_work_groups_legacy.py` / `legacy_*.dart`.

## Contract and launch

The server contract is `cortendesk/docs/session-work-groups.md`, including Client
organization management API v2. The server implementation/deployment belongs to
the separate Console project. This client does not deploy it or use admin tokens.

Desktop launches preflight with the existing device work-groups endpoint before
opening the transport. One option is automatic; multiple options have no default
unless an eligible origin was captured from the Organizations tab. Do not select
continues without an assignment; Cancel aborts the launch. The intent and its
completed-preflight flag travel with the launch/window arguments, never in a
shared device-preference cache. After authentication, the client resolves the
exact GUID using the decimal-string u64 connection ID, target and connection
type, rechecks choices and saves only an eligible selection for that session.
A failed connection never creates a session assignment.

## Organization management

V2 capability detection and server permissions control search, creation and
attachment. Every request retains the client Bearer and JSON headers; no
fallback to admin credentials or Console cookies is used. Creation takes name,
note and eligible user-group IDs from the server form contract. Returned defaults
are honored. A created ID is selected and used for the subsequent operation.
The same creation/attachment UUID and frozen payload are reused after an unknown
network result. Retry-After blocks premature mutation retries. An explicit 422
attachment rejection permits selecting a corrected candidate.

For an unconfirmed session, attachment and first assignment use the server's
atomic `attach_device_if_needed` operation only when v2 and the required
permission are confirmed. Confirmed assignments cannot change. Adding another
organization uses the device attachment API without altering the session.
Successful assignment is reread before displaying its recorded name.

## Toolbar and closing

The desktop panel reuses original action widgets and permission checks; Chat and
Recording are under More. The visible return handle or unassigned amber badge
is movable within the window. No invisible wide hover target is installed. Pin
keeps the panel visible; active menus/dialogs suspend automatic collapse.
Unsupported session-accounting servers retain the original toolbar path.

Intentional final-session closure offers the shared organization editor only
when v2 says the device and session are unassigned. Save and end waits for the
confirmed snapshot; End without organization and Return to session remain
explicit. The native willSessionCloseCloseSession check excludes closing a lone
display window while the transport continues elsewhere. Cached display windows
read the same exact session without repeating preflight. A fresh confirmed
snapshot suppresses an obsolete closing reminder. Per-instance request scopes
isolate simultaneous windows in the native URL-keyed HTTP bridge.

## Validation and regression surface

Supported-source guards and Dart syntax checks cover both bases. Executable Dart
protocol tests cover exact IDs, authorization, immutable choices, retry UUIDs and
rate limits. Flutter tests cover selection/dismissal, closing confirmation,
additional attachment, stale display snapshots, visible-handle hit testing and
bounds. A complete desktop analyzer comparison with generated bridge files found
zero original errors and zero patched errors. Component previews use native
Flutter rendering with Roboto and Material Icons; demonstration action slots
are not a complete running client.

Changed existing runtime paths: FfiModel peer-info capture/state; common dialog
manager first-frame cleanup; intentional-close helper; desktop window launch
argument plumbing and five session-page initializers; desktop toolbar rendering
and submenu lifecycle. Original control/display/keyboard/chat/call/record/close
action bodies are preserved and checked in source tests. See
`REMOTE_TOOLBAR_AUDIT_RU.md` for the inventory. No native connection protocol,
server access control, existing Accessible devices/Colleagues filtering,
publication or update-channel behavior is changed by this manifest.

A full native client build and authenticated multi-machine end-to-end test are
still required before distributing a release. These changes alone neither
build nor publish clients and do not enable unavailable server APIs.
