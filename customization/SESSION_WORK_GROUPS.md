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
automatically; multiple groups open a picker. Launching from a specific organization
preselects its numeric ID only if the authoritative session choices include it;
other tabs have no preselection. The origin is listed first with a small caption.
The buttons are "Do not select" and "Confirm". "Do not select"
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
translation keys, and the three existing platform preparation paths. Desktop
organization origins travel in an asynchronous launch zone, the existing
window-argument JSON, and optional fields on the five session page types. Their
FFI initialization captures the hint; the terminal manager assigns it only to a
new transport, never to an existing shared terminal connection. There is no
target-keyed pending-choice map or persistent preference. Existing
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

## Organizations catalog API (new server increment required)

The desktop Organizations tab reads the separate Bearer-authenticated endpoint:

`GET /api/statusdesk/organizations?current=1&pageSize=100`

```json
{"total":2,"data":[
  {"id":10,"name":"Organization A","peer_ids":["123456789"]},
  {"id":20,"name":"Organization B","peer_ids":["123456789"]}
]}
```

`total` counts organizations; pagination is over organizations, with stable order
and each row containing its complete, deduplicated device ID list. Device IDs
must be strings. Include each active device in its primary and additional work
organizations, intersected with the current user's existing device visibility.
Return no empty organizations. This endpoint must not grant access, change the
existing accessible-groups endpoint, or reveal other devices in these groups.

The client intersects these IDs with its existing authorized peer list, so a
device appears once in each matching organization. Group selection uses IDs,
including when two names happen to match. With no specific organization selected,
the view shows the union without a preferred organization. Only this tab uses the
new catalog; Accessible devices and Colleagues keep their current filtering.

The catalog is kept in the owning tab's memory and discarded on account change;
it is never added to the existing on-disk groups cache. 404/405/501 retain the
primary-group view with no guessed IDs. Authorization/network/validation errors
show a retry banner and do not masquerade as an unsupported server. The existing
session GUID/read/write API and its authorization rules remain unchanged.
