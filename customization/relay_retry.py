"""Reuse RustDesk's relay hint for transport resets without an OS error number."""
from pathlib import Path


def apply(root, edits):
    def replace(name, old, new):
        path = root/name
        source = edits.get(path, path.read_text(encoding='utf-8'))
        if source.count(old) != 1:
            raise ValueError('Incompatible relay retry source: '+name)
        edits[path] = source.replace(old, new, 1)

    path = root/'src/client.rs'
    source = edits.get(path, path.read_text(encoding='utf-8'))
    if 'mod rdgen_relay_retry;' in source:
        raise ValueError('Relay retry already applied')
    edits[path] = 'mod rdgen_relay_retry;\n'+source
    replace('src/client.rs',
            '                || (!err.contains("Failed") && err.contains("deadline")))',
            '''                || (!err.contains("Failed") && err.contains("deadline"))
                || (cfg!(feature = "flutter") && rdgen_relay_retry::is_transport_error(&err)))''')
    replace('src/client/io_loop.rs',
            '                                    self.handler.msgbox("error", "Connection Error", "Reset by the peer", "");',
            '''                                    if cfg!(feature = "flutter") {
                                        self.handler.on_establish_connection_error("Reset by the peer".to_owned());
                                    } else {
                                        self.handler.msgbox("error", "Connection Error", "Reset by the peer", "");
                                    }''')
    # Keep relay policy for this session, but don't mark the peer for persistence.
    replace('src/ui_session_interface.rs', '''            // An explicit retry-via-relay is a decision about this peer, not transport
            // necessity: Relay-only ICE for this round like any force-always-relay session,
            // and it is the one kind of relay that belongs in the peer's saved config.
            lc.policy_relay = true;
            lc.peer_relay = true;''', '''            lc.policy_relay = true;
            if !cfg!(feature = "flutter") {
                lc.peer_relay = true;
            }''')
    edits[root/'src/client/rdgen_relay_retry.rs'] = Path(__file__).with_name('relay_retry.rs').read_text(encoding='utf-8')
