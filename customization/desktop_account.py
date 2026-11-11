"""Desktop account header, independent of the optional compact layout."""
import json
from pathlib import Path


def apply(root):
    path = root/'flutter/lib/desktop/pages/connection_page.dart'
    source = path.read_text(encoding='utf-8')
    old = '''            Row(
              children: [
                Flexible(child: _buildRemoteIDTextField(context)),
              ],
            )'''
    new = '''            Row(crossAxisAlignment: CrossAxisAlignment.center, children: [
              Expanded(child: Align(alignment: Alignment.centerLeft,
                child: _buildRemoteIDTextField(context))),
              const SizedBox(width: 12),
              const SizedBox(width: 180, child: RdgenDesktopAccount()),
            ])'''
    if source.count(old) != 1:
        raise ValueError('Incompatible desktop account header')
    edits = {path: "import '../../models/rdgen_desktop_account.dart';\n" + source.replace(old, new, 1)}
    labels = {'Open web panel': 'Войти в панель', 'Not signed in': 'Вход не выполнен'}
    for path in (root/'src/lang').glob('*.rs'):
        if path.name == 'en.rs': continue
        source = path.read_text(encoding='utf-8')
        anchor = '    ].iter().cloned().collect();'
        if source.count(anchor) != 1:
            raise ValueError('Incompatible account translation: '+path.name)
        entries = ''.join('\n        ('+json.dumps(k)+', '+json.dumps(v if path.name == 'ru.rs' else '', ensure_ascii=False)+'),' for k,v in labels.items() if json.dumps(k) not in source)
        if entries:
            prefix, suffix = source.split(anchor)
            edits[path] = prefix.rstrip().removesuffix(',')+','+entries+'\n'+anchor+suffix
    edits[root/'flutter/lib/models/rdgen_desktop_account.dart'] = Path(__file__).with_name('desktop_account.dart').read_text(encoding='utf-8')
    for path, text in edits.items(): path.write_text(text, encoding='utf-8')
