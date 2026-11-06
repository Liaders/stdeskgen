"""Add a users-only view over the existing server-authorized group data."""


def add_colleagues(root, edits, replace, profile, standalone=False):
    group = root / 'flutter/lib/common/widgets/my_group.dart'
    source = edits.get(group, group.read_text(encoding='utf-8'))
    source = source.replace('MyGroup', 'RdgenColleagues')
    source = source.replace('  RxBool get isSelectedDeviceGroup => gFFI.groupModel.isSelectedDeviceGroup;',
                            '  final isSelectedDeviceGroup = false.obs;')
    source = source.replace('  RxString get selectedAccessibleItemName =>\n      gFFI.groupModel.selectedAccessibleItemName;',
                            "  final selectedAccessibleItemName = ''.obs;")
    source = source.replace('  RxString get searchAccessibleItemNameText =>\n      gFFI.groupModel.searchAccessibleItemNameText;',
                            "  final searchAccessibleItemNameText = ''.obs;")
    source = source.replace('static TextEditingController searchUserController', 'final TextEditingController searchUserController')
    source = source.replace('  Widget _buildLandscape() {',
        '  @override\n  void dispose() {\n    searchUserController.dispose();\n    super.dispose();\n  }\n\n  Widget _buildLandscape() {')
    source = source.replace('rdgen-panel-group-width-v1', 'rdgen-panel-colleagues-width-v1')
    start = source.index('      final deviceGroupItems =')
    end = source.index('      var maxHeight', start)
    source = source[:start] + '''      listView(bool isPortrait) => userItems.isEmpty
          ? Center(child: Text(translate('Empty')))
          : ListView.builder(
              shrinkWrap: isPortrait,
              itemCount: userItems.length,
              itemBuilder: (context, index) =>
                  _buildUserItem(userItems[index], displayNameCount));
''' + source[end:]
    source = source[:source.index('  Widget _buildDeviceGroupItem(')] + '}\n'
    source = source.replace('RdgenColleaguesPeerView(\n                menuPadding: widget.menuPadding,\n              )', '''Obx(() {
                final selected = selectedAccessibleItemName.value;
                final search = searchAccessibleItemNameText.value.toLowerCase();
                return RdgenColleaguesPeerView(
                  key: ValueKey('$selected/$search'),
                  selected: selected, search: search,
                  menuPadding: widget.menuPadding);
              })''')
    source = source.replace("import '../../common.dart';", "import '../../common.dart';\nimport '../../models/peer_model.dart';\nimport '../../models/peer_tab_model.dart';\nimport 'peer_card.dart';")
    source += '''
class RdgenColleaguesPeerView extends BasePeersView {
  RdgenColleaguesPeerView({Key? key, required String selected,
      required String search, EdgeInsets? menuPadding}) : super(
    key: key,
    peerTabIndex: PeerTabIndex.group,
    peerFilter: (Peer peer) => gFFI.groupModel.users.any((user) =>
      user.name == peer.loginName &&
      (selected.isEmpty || user.name == selected) &&
      (search.isEmpty || user.name.toLowerCase().contains(search) ||
        user.displayNameOrName.toLowerCase().contains(search))),
    peerCardBuilder: (Peer peer) => MyGroupPeerCard(
      peer: peer, menuPadding: menuPadding));
}
'''
    edits[root / 'flutter/lib/common/widgets/rdgen_colleagues.dart'] = source
    if standalone:
        if source.count('onPressed: loginDialog,')!=1:raise ValueError('Incompatible colleagues login action')
        edits[root / 'flutter/lib/common/widgets/rdgen_colleagues.dart'] = source.replace(
            'onPressed: loginDialog,',
            'onPressed: () async { await loginDialog(); await gFFI.groupModel.pull(force: true); },')
        replace('src/lang/ru.rs', '("Accessible devices", "Доступные устройства"),', '("Accessible devices", "Доступные устройства"),\n        ("Colleagues", "Коллеги"),')
        return
    model = 'flutter/lib/models/peer_tab_model.dart'
    replace(model, 'maxTabCount = 5;', 'maxTabCount = 6;')
    replace(model, "    'Accessible devices',", "    'Accessible devices',\n    'Colleagues',")
    replace(model, '    IconFont.deviceGroupFill,', '    IconFont.deviceGroupFill,\n    Icons.people,')
    anchor = '    !(bind.isDisableGroupPanel() || bind.isDisableAccount()),'
    replace(model, anchor, anchor + '\n' + anchor)
    replace('src/lang/ru.rs', '("Accessible devices", "Доступные устройства"),', '("Accessible devices", "Доступные устройства"),\n        ("Colleagues", "Коллеги"),')
    # Accept the old five-tab preferences and append the new tab.
    replace(model, 'if (decodeList.length == _isVisible.length) {', 'if (decodeList.length == 5) decodeList.add(true);\n        if (decodeList.length == _isVisible.length) {')
    replace(model, 'if (decodeList.length == maxTabCount) {', 'if (decodeList.length == 5) decodeList.add(5);\n        if (decodeList.length == maxTabCount) {')
    page = 'flutter/lib/common/widgets/peer_tab_page.dart'
    replace(page, "import 'dart:ui' as ui;", "import 'dart:ui' as ui;\nimport 'rdgen_colleagues.dart';")
    replace(page, '  ];\n  RelativeRect?', '''    _TabEntry(RdgenColleagues(menuPadding: _menuPadding()),
      ({dynamic hint}) => gFFI.groupModel.pull(force: hint == null)),
  ];
  RelativeRect?''')
    replace(page, 'offstage: model.currentTab != index.index,', 'offstage: model.currentTab != index.index && !(index == PeerTabIndex.group && model.currentTab == 5),')
    path = root / page
    edits[path] = edits[path].replace('model.currentTab == PeerTabIndex.group.index', '(model.currentTab == PeerTabIndex.group.index || model.currentTab == 5)')
