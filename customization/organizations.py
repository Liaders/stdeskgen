"""Groups-only desktop view over the existing server-authorized device groups."""
import json
import re
from pathlib import Path


def add_organizations(root, edits, replace):
    group = root/'flutter/lib/common/widgets/my_group.dart'
    source = edits.get(group, group.read_text(encoding='utf-8'))

    def change(old, new, count=1):
        nonlocal source
        if source.count(old) != count:
            raise ValueError('Incompatible organizations view: '+old)
        source = source.replace(old, new)

    source = source.replace('MyGroup', 'RdgenOrganizations')
    change('  RxBool get isSelectedDeviceGroup => gFFI.groupModel.isSelectedDeviceGroup;',
           '  final isSelectedDeviceGroup = true.obs;')
    change('  RxString get selectedAccessibleItemName =>\n      gFFI.groupModel.selectedAccessibleItemName;',
           "  final selectedAccessibleItemName = ''.obs;")
    change('  RxString get searchAccessibleItemNameText =>\n      gFFI.groupModel.searchAccessibleItemNameText;',
           "  final searchAccessibleItemNameText = ''.obs;")
    change('static TextEditingController searchUserController', 'final TextEditingController searchUserController')
    change('  Widget _buildLandscape() {', '''  late final RdgenOrganizationData _organizationData;

  @override
  void initState() {
    super.initState();
    _organizationData = RdgenOrganizationData();
  }

  Widget _buildLandscape() {''')
    change('  Widget _buildLandscape() {', '''  @override
  void dispose() {
    _organizationData.dispose();
    searchUserController.dispose();
    super.dispose();
  }

  Widget _buildLandscape() {''')
    source = source.replace('rdgen-panel-group-width-v1', 'rdgen-panel-organizations-width-v1')
    start = source.index('      final userItems =')
    end = source.index('      final deviceGroupItems =', start)
    source = source[:start]+source[end:]
    start = source.index('      listView(bool isPortrait) =>')
    end = source.index('      var maxHeight', start)
    source = source[:start]+'''      listView(bool isPortrait) => deviceGroupItems.isEmpty
          ? Center(child: Text(translate('Empty')))
          : ListView.builder(
              shrinkWrap: isPortrait,
              itemCount: deviceGroupItems.length,
              itemBuilder: (context, index) =>
                  _buildDeviceGroupItem(deviceGroupItems[index]));
'''+source[end:]
    start = source.index('  Widget _buildUserItem(')
    end = source.index('  Widget _buildDeviceGroupItem(', start)
    source = source[:start]+source[end:]
    change('RdgenOrganizationsPeerView(\n                menuPadding: widget.menuPadding,\n              )', '''Obx(() {
                final selected = selectedAccessibleItemName.value;
                final search = searchAccessibleItemNameText.value.toLowerCase();
                return RdgenOrganizationsPeerView(
                  key: ValueKey('$selected/$search'),
                  selected: selected, search: search, organizations: _organizationData.groups,
                  menuPadding: widget.menuPadding);
              })''', 2)
    change("import '../../common.dart';", "import '../../common.dart';\nimport '../../models/peer_model.dart';\nimport '../../models/peer_tab_model.dart';\nimport '../../models/rdgen_organization_catalog.dart';\nimport '../../models/rdgen_organization_data.dart';\nimport '../../models/rdgen_work_group_origin.dart';\nimport 'peer_card.dart';")
    change('final deviceGroupItems = gFFI.groupModel.deviceGroups.where', 'final deviceGroupItems = _organizationData.groups.where')
    change('Widget _buildDeviceGroupItem(DeviceGroupPayload deviceGroup)', 'Widget _buildDeviceGroupItem(WorkOrganization deviceGroup)')
    change('    final name = deviceGroup.name;', '    final name = deviceGroup.name;\n    final selectionKey = deviceGroup.selectionKey;')
    change('selectedAccessibleItemName.value != name', 'selectedAccessibleItemName.value != selectionKey')
    change('selectedAccessibleItemName.value = name;', 'selectedAccessibleItemName.value = selectionKey;')
    change('selectedAccessibleItemName.value == name', 'selectedAccessibleItemName.value == selectionKey')
    change('          Expanded(\n              child: Obx', '''          buildErrorBanner(context, loading: _organizationData.loading,
              err: _organizationData.error, retry: _organizationData.reload,
              close: () => _organizationData.error.value = ''),
          Expanded(
              child: Obx''')
    source += '''
class RdgenOrganizationsPeerView extends BasePeersView {
  RdgenOrganizationsPeerView({Key? key, required String selected,
      required String search, required List<WorkOrganization> organizations,
      EdgeInsets? menuPadding}) : super(
    key: key,
    peerTabIndex: PeerTabIndex.group,
    peerFilter: (Peer peer) => organizations.any((group) =>
      group.peerIds.contains(peer.id) &&
      (selected.isEmpty || group.selectionKey == selected) &&
      (search.isEmpty || group.name.toLowerCase().contains(search))),
    peerCardBuilder: (Peer peer) {
      final card = MyGroupPeerCard(peer: peer, menuPadding: menuPadding);
      final origins = organizations.where((group) => group.selectionKey == selected &&
          group.peerIds.contains(peer.id) && group.id != null);
      return origins.isEmpty ? card : RdgenWorkGroupOrigin(
          groupId: origins.first.id!, child: card);
    });
}
'''
    edits[root/'flutter/lib/common/widgets/rdgen_organizations.dart'] = source
    for name in ['organization_catalog', 'organization_data', 'work_group_origin']:
        edits[root/f'flutter/lib/models/rdgen_{name}.dart'] = Path(__file__).with_name(name+'.dart').read_text(encoding='utf-8')
    edits[root/'flutter/lib/models/rdgen_session_work_groups.dart'] = Path(__file__).with_name('session_work_groups.dart').read_text(encoding='utf-8')

    model = 'flutter/lib/models/peer_tab_model.dart'
    original = edits.get(root/model, (root/model).read_text(encoding='utf-8'))
    old_count = int(re.search(r'maxTabCount = (\d+);', original).group(1))
    if old_count not in (5, 6): raise ValueError('Incompatible organizations tab count')
    replace(model, f'maxTabCount = {old_count};', f'maxTabCount = {old_count+1};')
    label = 'Colleagues' if old_count == 6 else 'Accessible devices'
    replace(model, f"    '{label}',", f"    '{label}',\n    'Organizations',")
    icon = 'Icons.people' if old_count == 6 else 'IconFont.deviceGroupFill'
    replace(model, f'    {icon},', f'    {icon},\n    Icons.apartment_outlined,')
    replace(model, '  ]);\n  final List<bool> _isVisible',
            '    !(bind.isDisableGroupPanel() || bind.isDisableAccount()),\n  ]);\n  final List<bool> _isVisible')
    replace(model, 'if (decodeList.length == _isVisible.length) {',
            f'if (decodeList.length == {old_count}) decodeList.add(true);\n        if (decodeList.length == _isVisible.length) {{')
    replace(model, 'if (decodeList.length == maxTabCount) {',
            f'if (decodeList.length == {old_count}) decodeList.add({old_count});\n        if (decodeList.length == maxTabCount) {{')
    from tab_order import add_initial_order
    add_initial_order(replace, with_colleagues=old_count == 6)
    page = 'flutter/lib/common/widgets/peer_tab_page.dart'
    replace(page, "import 'dart:ui' as ui;", "import 'dart:ui' as ui;\nimport 'rdgen_organizations.dart';")
    replace(page, '  ];\n  RelativeRect?', '''    _TabEntry(RdgenOrganizations(menuPadding: _menuPadding()),
      ({dynamic hint}) => gFFI.groupModel.pull(force: hint == null)),
  ];
  RelativeRect?''')
    old = 'offstage: model.currentTab != index.index,' if old_count == 5 else 'offstage: model.currentTab != index.index && !(index == PeerTabIndex.group && model.currentTab == 5),'
    tabs = f'model.currentTab == {old_count}' if old_count == 5 else f'(model.currentTab == 5 || model.currentTab == {old_count})'
    replace(page, old, f'offstage: model.currentTab != index.index && !(index == PeerTabIndex.group && {tabs}),')
    edits[root/page] = edits[root/page].replace('model.currentTab == PeerTabIndex.group.index',
        f'(model.currentTab == PeerTabIndex.group.index || model.currentTab == {old_count})')
    for path in (root/'src/lang').glob('*.rs'):
        if path.name == 'en.rs': continue
        text = edits.get(path, path.read_text(encoding='utf-8'))
        anchor = '    ].iter().cloned().collect();'
        if text.count(anchor) != 1: raise ValueError('Incompatible organizations translation')
        prefix, suffix = text.split(anchor)
        translations = {'Organizations': 'Организации', 'Failed to load organizations': 'Не удалось загрузить организации'}
        entries = ''.join('\n        ('+json.dumps(k)+', '+json.dumps(v if path.name == 'ru.rs' else '', ensure_ascii=False)+'),' for k, v in translations.items() if '"'+k+'"' not in text)
        edits[path] = prefix.rstrip().removesuffix(',')+','+entries+'\n'+anchor+suffix
