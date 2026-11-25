"""Desktop new-device view; creation time is server-owned, never first-seen locally."""
import json
import re
from pathlib import Path


def add_new_devices(root, edits, replace):
    model = 'flutter/lib/models/peer_tab_model.dart'
    source = edits[root/model]
    count = int(re.search(r'maxTabCount = (\d+);', source).group(1))
    index = count
    replace(model, f'maxTabCount = {count};', f'maxTabCount = {count+1};')
    replace(model, "    'Organizations',", "    'Organizations',\n    'New devices',")
    replace(model, '    Icons.apartment_outlined,', '    Icons.apartment_outlined,\n    Icons.auto_awesome,')
    replace(model, '  ]);\n  final List<bool> _isVisible',
            '    !(bind.isDisableGroupPanel() || bind.isDisableAccount()),\n  ]);\n  final List<bool> _isVisible')
    # Deliberately reset visibility AND order once for this rollout. Do not touch
    # rdgen-navigation-style-v1, which belongs to the user's text/icon preference.
    order = [0, 3, 1, count-1] + ([5] if count == 7 else []) + [index, 2, 4]
    visible = [True] * (count+1)
    visible[2] = visible[4] = False
    marker = 'rdgen-peer-tabs-new-devices-v3'
    replace(model, '    // init currentTab', f'''    if (bind.getLocalFlutterOption(k: '{marker}') != 'Y') {{
      orders.setAll(0, {order});
      _isVisible.setAll(0, {json.dumps(visible)});
      _rdgenSaveNewDeviceTabs();
    }}
    // init currentTab''')
    replace(model, '  setCurrentTab(int index) {', f'''  Future<void> _rdgenSaveNewDeviceTabs() async {{
    try {{
      await bind.setLocalFlutterOption(k: kOptionPeerTabOrder, v: jsonEncode(orders));
      await bind.setLocalFlutterOption(k: kOptionPeerTabVisible, v: jsonEncode(_isVisible));
      await bind.setLocalFlutterOption(k: kOptionPeerCardUiType, v: '2');
      await bind.setLocalFlutterOption(k: '{marker}', v: 'Y');
    }} catch (e) {{ debugPrint('Failed to save new device tab preferences: $e'); }}
  }}

  setCurrentTab(int index) {{''')
    peer = 'flutter/lib/models/peer_model.dart'
    replace(peer, '  String note;', '  String note;\n  DateTime? rdgenCreatedAt;')
    replace(peer, "        sameServer = json['same_server'];", "        sameServer = json['same_server'],\n        rdgenCreatedAt = DateTime.tryParse(json['created_at'] is String ? json['created_at'] : '');")
    replace(peer, '  Map<String, dynamic> toGroupCacheJson() {\n    return <String, dynamic>{',
            "  Map<String, dynamic> toGroupCacheJson() {\n    return <String, dynamic>{\n      'created_at': rdgenCreatedAt?.toUtc().toIso8601String(),")
    replace('flutter/lib/models/group_model.dart', '                final peer = PeerPayload.toPeer(peerPayload);',
            "                final peer = PeerPayload.toPeer(peerPayload);\n                peer.rdgenCreatedAt = DateTime.tryParse(p['created_at'] is String ? p['created_at'] : '');")
    # An optional comparator keeps all upstream search, view modes, selection and
    # online updates; other tabs retain their original sorting.
    path = root/'flutter/lib/common/widgets/peers_view.dart'
    text = edits.get(path, path.read_text(encoding='utf-8'))
    text = text.replace('  final PeerFilter? peerFilter;', '  final PeerFilter? peerFilter;\n  final Comparator<Peer>? rdgenComparator;')
    text = re.sub(r'(?m)^(\s*)this.peerFilter,$', r'\1this.peerFilter,\n\1this.rdgenComparator,', text)
    text = text.replace('        peerFilter: peerFilter,', '        peerFilter: peerFilter,\n        rdgenComparator: rdgenComparator,')
    text = text.replace('    if (widget.peers.loadEvent != LoadEvent.recent) {',
        '    if (widget.rdgenComparator != null) {\n      peers.sort(widget.rdgenComparator);\n    } else if (widget.peers.loadEvent != LoadEvent.recent) {')
    text = text.replace('  final Comparator<Peer>? rdgenComparator;', '  final Comparator<Peer>? rdgenComparator;\n  final double rdgenCardFooterHeight;')
    text = re.sub(r'(?m)^(\s*)this.rdgenComparator,$', r'\1this.rdgenComparator,\n\1this.rdgenCardFooterHeight = 0,', text)
    text = text.replace('        rdgenComparator: rdgenComparator,', '        rdgenComparator: rdgenComparator,\n        rdgenCardFooterHeight: rdgenCardFooterHeight,')
    for height in (140, 42):
        text = text.replace(f'height: {height}, child: visibilityChild', f'height: {height} + widget.rdgenCardFooterHeight, child: visibilityChild')
    edits[path] = text
    card = 'flutter/lib/common/widgets/peer_card.dart'
    replace(card, "import 'package:flutter/material.dart';", "import 'package:flutter/material.dart';\nimport 'rdgen_new_device_row_metadata.dart';")
    replace(card, '                isPortrait\n                    ? checkBoxOrActionMorePortrait(peer)', '''                if (RdgenNewDeviceRowMetadata.of(context) != null)
                  RdgenNewDeviceRowMetadata.of(context)!,
                isPortrait
                    ? checkBoxOrActionMorePortrait(peer)''')
    page = 'flutter/lib/common/widgets/peer_tab_page.dart'
    replace(page, '    final uiType = bind.getLocalFlutterOption(k: kOptionPeerCardUiType);', f'''    final uiType = bind.getLocalFlutterOption(k: '{marker}') != 'Y'
        ? '2' : bind.getLocalFlutterOption(k: kOptionPeerCardUiType);''')
    replace(page, "import 'rdgen_organizations.dart';", "import 'rdgen_organizations.dart';\nimport 'rdgen_new_devices.dart';")
    replace(page, '  ];\n  RelativeRect?', '''    _TabEntry(RdgenNewDevices(menuPadding: _menuPadding()),
      ({dynamic hint}) => gFFI.groupModel.pull(force: hint == null, rdgenCatalog: hint == null)),
  ];
  RelativeRect?''')
    # Wrap switch bar in one reactive clock: count/colour work in both modes.
    replace(page, '  Widget _createSwitchBar(BuildContext context) {', '''  Widget _createSwitchBar(BuildContext context) => RdgenNewDeviceClock(
    builder: (now) => Obx(() => _rdgenSwitchBar(context, now,
      gFFI.groupModel.peers.where((p) => rdgenIsNewDevice(p, now)).length)));

  Widget _rdgenSwitchBar(BuildContext context, DateTime now, int newCount) {''')
    replace(page, '          final color = selected', f'          final color = t == {index} && newCount > 0 ? (selected ? const Color(0xFFEAB84B) : const Color(0xFFD29922)) : selected')
    path = root/page
    text = edits[path]
    anchor = 'child: (isDesktop && _rdgenTextTabs'
    start = text.index(anchor)
    end = text.index('\n', text.index(': Icon(model.tabIcon(t), color: color))', start))
    text = text[:start] + f'''child: Row(mainAxisSize: MainAxisSize.min, children: [
                          (isDesktop && _rdgenTextTabs
                            ? Transform.translate(offset: const Offset(0, 5),
                                child: Text(model.tabTooltip(t), style: TextStyle(color: color)))
                            : Icon(model.tabIcon(t), color: color)),
                          if (t == {index} && newCount > 0)
                            Padding(padding: const EdgeInsets.only(left: 4),
                              child: Transform.translate(offset: Offset(0, _rdgenTextTabs ? 5 : 0),
                                child: RdgenNewDeviceCount(count: newCount, selected: selected))),
                        ])''' + text[end:]
    text, n = re.subn(r'(offstage: model.currentTab != index.index && )(.+),',
        lambda m: m[1] + f'!(index == PeerTabIndex.group && model.currentTab == {index}) && ' + m[2] + ',', text)
    if n != 1: raise ValueError('Incompatible new devices refresh control')
    text = text.replace('offstage: model.currentTab == PeerTabIndex.recent.index,', f'offstage: model.currentTab == PeerTabIndex.recent.index || model.currentTab == {index},')
    text = text.replace('if (model.currentTab != PeerTabIndex.recent.index) PeerSortDropdown(),', f'if (model.currentTab != PeerTabIndex.recent.index && model.currentTab != {index}) PeerSortDropdown(),')
    edits[path] = text
    edits[root/'flutter/lib/common/widgets/rdgen_new_devices.dart'] = Path(__file__).with_name('new_devices.dart').read_text(encoding='utf-8')
    edits[root/'flutter/lib/common/widgets/rdgen_new_device_row_metadata.dart'] = Path(__file__).with_name('new_device_row_metadata.dart').read_text(encoding='utf-8')
    translations = {'New devices': 'Новые', 'Just now': 'Только что', 'Minutes ago': 'минут назад', 'Hours ago': 'часов назад', 'No organization': 'Без организации'}
    for path in (root/'src/lang').glob('*.rs'):
        if path.name == 'en.rs': continue
        text = edits.get(path, path.read_text(encoding='utf-8'))
        anchor = '    ].iter().cloned().collect();'
        prefix, suffix = text.split(anchor)
        entries = ''.join('\n        (' + json.dumps(k) + ', ' + json.dumps(v if path.name == 'ru.rs' else '', ensure_ascii=False) + '),' for k,v in translations.items() if '"'+k+'"' not in text)
        edits[path] = prefix.rstrip().removesuffix(',') + ',' + entries + '\n' + anchor + suffix
