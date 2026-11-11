"""Desktop account header, independent of the optional compact layout."""
import json
from pathlib import Path


def apply(root):
    path = root/'flutter/lib/desktop/pages/connection_page.dart'
    source = path.read_text(encoding='utf-8')
    def replace(old, new):
        nonlocal source
        if source.count(old) != 1:
            raise ValueError('Incompatible desktop account header')
        source = source.replace(old, new, 1)

    layout = 'RdgenConnectionLayout' if 'child: RdgenConnectionLayout(' in source else 'Column'
    options = 'compact: rdgenSlimUi.value, ' if layout == 'RdgenConnectionLayout' else ''
    replace('      child: Ink(\n        child: '+layout+'(',
            '      child: Ink(\n        child: RdgenAccountGroup('+options+'child: '+layout+'(')
    replace('          ],\n        ),\n      ),\n    );\n    return Container(', '          ],\n        )),\n      ),\n    );\n    return Container(')
    # Expand the existing frame to include the account; its padding is shared.
    for old in ('width: 320 + 20 * 2,',
                'width: rdgenSlimUi.value ? double.infinity : 320 + 20 * 2,'):
        if old in source: replace(old, 'width: double.infinity,')
    for old in ('constraints: const BoxConstraints(maxWidth: 600), child: w',
                'constraints: BoxConstraints(maxWidth: rdgenSlimUi.value ? double.infinity : 600), child: w'):
        if old in source: replace(old, 'constraints: const BoxConstraints(maxWidth: double.infinity), child: w')
    for old in (').paddingOnly(left: 12.0)),',
                ').paddingOnly(left: 12.0, right: rdgenSlimUi.value ? 12.0 : 0)),'):
        if old in source: replace(old, ').paddingOnly(left: 12.0, right: 12.0)),')
    edits = {path: "import '../../models/rdgen_desktop_account.dart';\n" + source}
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
