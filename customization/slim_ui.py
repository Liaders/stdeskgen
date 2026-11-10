"""Opt-in desktop density, preserving the local-ID sidebar and typography."""
import hashlib
import json
from pathlib import Path

# The layout reuses the upstream title, autocomplete and action widgets.
CONNECTION_LAYOUT_HASHES = {
    '144176683be03e37c3fa4e9a9ae504a69b0a57de6a8e4daf265d94e689407151',
}


def apply(root):
    edits = {}

    def replace(name, old, new):
        path = root/name
        source = edits.get(path, path.read_text(encoding='utf-8'))
        if source.count(old) != 1:
            raise ValueError('Incompatible Slim UI source: '+name)
        edits[path] = source.replace(old, new, 1)

    connection = 'flutter/lib/desktop/pages/connection_page.dart'
    source = (root/connection).read_text(encoding='utf-8')
    start = source.index('  Widget _buildRemoteIDTextField(BuildContext context) {')
    method = source[start:]
    if hashlib.sha256(method.encode()).hexdigest() not in CONNECTION_LAYOUT_HASHES:
        raise ValueError('Slim UI: remote-ID layout changed; review adapter for this RustDesk version')
    imports = {
        connection: "import '../../models/rdgen_slim_ui.dart';",
        'flutter/lib/common/widgets/peers_view.dart': "import '../../models/rdgen_slim_ui.dart';",
        'flutter/lib/common/widgets/peer_tab_page.dart': "import '../../models/rdgen_slim_ui.dart';",
        'flutter/lib/common/widgets/my_group.dart': "import '../../models/rdgen_slim_ui.dart';",
        'flutter/lib/desktop/pages/desktop_setting_page.dart': "import '../../models/rdgen_slim_ui.dart';",
    }
    for name, statement in imports.items():
        path = root/name
        edits[path] = statement+'\n'+path.read_text(encoding='utf-8')
    replace(connection, '''    return Column(
      children: [
        Expanded(''', '''    return Obx(() => Column(
      children: [
        Expanded(''')
    replace(connection, '''        if (!isOutgoingOnly) OnlineStatusWidget()
      ],
    );''', '''        if (!isOutgoingOnly) OnlineStatusWidget()
      ],
    ));''')
    replace(connection, ').marginOnly(top: 22),', ').marginOnly(top: rdgenSlimUi.value ? 4 : 22),')
    replace(connection, '            SizedBox(height: 12),', '            SizedBox(height: rdgenSlimUi.value ? 4 : 12),')
    replace(connection, '      width: 320 + 20 * 2,', '      width: rdgenSlimUi.value ? double.infinity : 320 + 20 * 2,')
    replace(connection, '      padding: const EdgeInsets.fromLTRB(20, 24, 20, 22),', '      padding: rdgenSlimUi.value ? const EdgeInsets.fromLTRB(12, 10, 12, 10) : const EdgeInsets.fromLTRB(20, 24, 20, 22),')
    replace(connection, '''      child: Ink(
        child: Column(''', '''      child: Ink(
        child: RdgenConnectionLayout(''')
    replace(connection, 'getConnectionPageTitle(context, false).marginOnly(bottom: 15)', 'getConnectionPageTitle(context, false).marginOnly(bottom: rdgenSlimUi.value ? 8 : 15)')
    replace(connection, '''contentPadding: const EdgeInsets.symmetric(
                                  horizontal: 15, vertical: 13)''', '''contentPadding: EdgeInsets.symmetric(
                                  horizontal: 15, vertical: rdgenSlimUi.value ? 6 : 13)''')
    replace(connection, 'constraints: const BoxConstraints(maxWidth: 600), child: w', 'constraints: BoxConstraints(maxWidth: rdgenSlimUi.value ? double.infinity : 600), child: w')

    peers = 'flutter/lib/common/widgets/peers_view.dart'
    replace(peers, '  final space = (isDesktop || isWebDesktop) ? 12.0 : 8.0;', '''  final space = (isDesktop || isWebDesktop) ? 12.0 : 8.0;
  double get _rdgenListSpace {
    final slim = rdgenSlimUi.value;
    return isDesktop && slim ? 4.0 : space;
  }''')
    replace(peers, '''                          return buildOnePeer(peers[index], false).marginOnly(
                              right: space,
                              top: index == 0 ? 0 : space / 2,
                              bottom: space / 2);''', '''                          return Obx(() => buildOnePeer(peers[index], false).marginOnly(
                              right: _rdgenListSpace,
                              top: index == 0 ? 0 : _rdgenListSpace / 2,
                              bottom: _rdgenListSpace / 2));''')
    tabs = 'flutter/lib/common/widgets/peer_tab_page.dart'
    replace(tabs, '''    return Expanded(
        child: child.marginSymmetric(
            vertical: (isDesktop || isWebDesktop) ? 12.0 : 6.0));''', '''    return Expanded(
        child: Obx(() => child.marginSymmetric(
            vertical: rdgenSlimUi.value && isDesktop ? 4.0 : (isDesktop || isWebDesktop) ? 12.0 : 6.0)));''')
    group = root/'flutter/lib/common/widgets/my_group.dart'
    source = edits[group]
    first = '    return InkWell(onTap: () {'
    last = '    )).marginSymmetric(horizontal: 12).marginOnly(bottom: 6);'
    if source.count(first) != 2 or source.count(last) != 2:
        raise ValueError('Incompatible Slim UI group rows')
    edits[group] = source.replace(first, '    return Obx(() => InkWell(onTap: () {').replace(last, '    )).marginSymmetric(horizontal: 12).marginOnly(bottom: rdgenSlimUi.value ? 3 : 6));')

    settings = 'flutter/lib/desktop/pages/desktop_setting_page.dart'
    replace(settings, "      _Card(title: 'Interface', children: [", """      _Card(title: 'Interface', children: [
        _Checkbox(label: 'Compact interface (Slim UI)',
          getValue: () => rdgenSlimUi.value,
          setValue: setRdgenSlimUi),""")
    translations = {'Compact interface (Slim UI)': 'Компактный интерфейс (Slim UI)'}
    for path in (root/'src/lang').glob('*.rs'):
        if path.name == 'en.rs': continue
        source = edits.get(path, path.read_text(encoding='utf-8'))
        if '"Compact interface (Slim UI)"' in source: continue
        anchor = '    ].iter().cloned().collect();'
        if source.count(anchor) != 1: raise ValueError('Incompatible Slim UI translation: '+path.name)
        prefix, suffix = source.split(anchor)
        entries = ''.join('\n        ('+json.dumps(k)+', '+json.dumps(v if path.name == 'ru.rs' else '', ensure_ascii=False)+'),' for k, v in translations.items())
        edits[path] = prefix.rstrip().removesuffix(',')+','+entries+'\n'+anchor+suffix
    edits[root/'flutter/lib/models/rdgen_slim_ui.dart'] = Path(__file__).with_name('slim_ui.dart').read_text(encoding='utf-8')
    for path, text in edits.items(): path.write_text(text, encoding='utf-8')
