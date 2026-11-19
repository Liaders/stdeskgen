"""Windows-only, cursor-service scoped accessibility workaround."""
from pathlib import Path


def apply(root):
    edits = {}
    def change(name, old, new):
        path = root/name
        text = edits.get(path, path.read_text(encoding='utf-8'))
        if text.count(old) != 1: raise ValueError('Incompatible headless cursor hook: '+name)
        edits[path] = text.replace(old, new)
    change('src/platform/mod.rs', 'pub mod windows;', 'pub mod windows;\n#[cfg(windows)]\npub mod rdgen_headless_cursor;')
    change('src/server/input_service.rs', 'struct StateCursor {', 'struct StateCursor {\n    #[cfg(windows)]\n    rdgen_cursor: crate::platform::rdgen_headless_cursor::Correction,')
    change('src/server/input_service.rs', '    if let Some(hcursor) = crate::get_cursor()? {', '''    let cursor = crate::get_cursor()?;
    #[cfg(windows)]
    state.rdgen_cursor.update(cursor.is_none());
    if let Some(hcursor) = cursor {''')
    # Recovery runs in the same desktop/session context as cursor polling.
    change('src/server/input_service.rs', 'impl super::service::Reset for StateCursor {', '''impl super::service::Reset for StateCursor {
    fn init(&mut self) {
        #[cfg(windows)]
        crate::platform::rdgen_headless_cursor::recover();
    }''')
    settings = 'flutter/lib/desktop/pages/desktop_setting_page.dart'
    change(settings, '      viewStyle(context),', '''      if (isWindows) _Card(title: 'Headless cursor correction', children: [
        _Checkbox(label: 'Automatically correct the cursor on computers without a mouse',
          getValue: () => bind.mainGetOptionSync(key: 'rdgen-auto-headless-cursor') != 'N',
          setValue: (value) async { await bind.mainSetOption(key: 'rdgen-auto-headless-cursor', value: value ? 'Y' : 'N'); }),
      ]),
      viewStyle(context),''')
    edits[root/'src/platform/rdgen_headless_cursor.rs'] = Path(__file__).with_suffix('.rs').read_text(encoding='utf-8')
    for path, text in edits.items(): path.write_text(text, encoding='utf-8')
