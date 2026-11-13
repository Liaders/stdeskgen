# Session organization selection

Client adapter for the Console contract in `cortendesk/docs/session-work-groups.md`
(Console `1.23.0-status.3`). No server deployment, database change, or access-rule
change is required here.

The initiating Flutter client captures the target ID, connection type, exact
decimal-string u64 connection ID, API URL and current client token at successful
peer authentication. It resolves the audit GUID independently of the optional
end-of-session note feature. Delayed audit delivery is retried for up to fourteen
seconds plus HTTP request time. The extra `statusdesk_work_group=1` query parameter
isolates this request from the note lookup in the native URL-keyed HTTP bridge;
the server ignores this parameter.

The session endpoint is authoritative. `automatic`, `selected`, `ungrouped` and
legacy/null need no prompt. For `required`, a single offered group is submitted
automatically; multiple groups open a picker without a preselected value. Cancel
sends no assignment. Save waits for `200 {saved:true}`; 409/422 trigger a fresh
read of the immutable server snapshot. Errors leave the session unassigned;
neither the device's primary group nor a previous connection is used as fallback.

State is held in memory per connection. No new preferences, credentials or group
cache are written to disk. Token changes stop subsequent requests. A pending
submission can finish after disconnect; new dialogs are suppressed if the
captured connection is no longer the current connection. Unsupported servers
retain their existing connection path. There is no organization-switch action
inside an established session.

Enabled in the Windows x64, macOS, Linux and Android preparation paths. Windows
x32/Sciter is deliberately unchanged. The receiving client needs no update for
this feature. No client build or publication is triggered by the adapter.

Regression surface: two hooks and a helper in Flutter `FfiModel`, additive
translation keys, and the three existing platform preparation paths. Existing
connection/authentication, notes, permissions and device-group filtering remain
unchanged. Incompatible upstream source anchors stop preparation explicitly.

Validation: `test_session_work_groups.py` checks source compatibility and adapter
coexistence, executes the pure-Dart HTTP contract tests, and runs the Flutter
picker widget test in an isolated host with the existing dialog API signatures.
CI covers RustDesk 1.5.0/1.5.1 and Flutter 3.24.5. These checks do not replace a full
client build or an authenticated end-to-end test against the deployed Console.

After making a test build (do not publish automatically), connect as a logged-in
operator to a device with two work groups. Choose one, then verify that exact
session in Console. Repeat with another simultaneous connection, cancellation,
one group, and a quick disconnect while Save is pending. Verify that the remote
computer receives no organization prompt and that access rights are unchanged.
