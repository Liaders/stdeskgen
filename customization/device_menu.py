"""Desktop device menus use authorized server mutations, never local aliases."""
from pathlib import Path


def apply(root):
    path = root/'flutter/lib/common/widgets/peer_card.dart'
    source = path.read_text(encoding='utf-8')
    def change(old, new, count=1):
        nonlocal source
        if source.count(old) != count:
            raise ValueError('Incompatible device menu: '+old[:100])
        source = source.replace(old, new)
    source = "import '../../models/rdgen_device_menu.dart';\n" + source
    change("(peer.alias.isEmpty\n          ? translate('Connect')\n          : '${translate('Connect')} ${peer.id}')", "translate('Connect')")
    change('      _connectAction(context),', '''      _connectAction(context),
      if (isDesktop && RdgenDeviceOrganizationOrigin.of(context))
        MenuEntryButton<String>(childBuilder: (style) => Text(translate('Add organization'), style: style),
          proc: () => rdgenManageDevice(context, peer.id), padding: menuPadding, dismissOnClicked: true),
      MenuEntryButton<String>(childBuilder: (style) => Text(translate('Copy ID'), style: style),
        proc: () => Clipboard.setData(ClipboardData(text: peer.id)), padding: menuPadding, dismissOnClicked: true),''', 5)
    # Existing Rename entries in all tabs now invoke the authenticated alias API.
    change('''        String oldName = await _getAlias(id);''', '''        if (isDesktop) { await rdgenManageDevice(context, id, aliasOnly: true); return; }
        String oldName = await _getAlias(id);''')
    change('    // menuItems.add(_renameAction(peer.id));', '''    if (isDesktop) menuItems.add(_renameAction(peer.id));
    // menuItems.add(_renameAction(peer.id));''')
    source = source.replace('_renameAction(String id)', '_renameAction(BuildContext context, String id)')
    source = source.replace('_renameAction(peer.id)', '_renameAction(context, peer.id)')
    start = source.index('class DiscoveredPeerCard extends BasePeerCard {')
    end = source.index('\nclass AddressBookPeerCard', start)
    body = source[start:end]
    if body.count('    return menuItems;') != 1: raise ValueError('Incompatible discovered alias menu')
    source = source[:start] + body.replace('    return menuItems;', '    if (isDesktop) menuItems.add(_renameAction(context, peer.id));\n    return menuItems;') + source[end:]
    old = "peer.alias.isEmpty ? formatID(peer.id) : peer.alias,"
    change(old, "isDesktop ? rdgenServerDeviceName(peer.id, peer.hostname) : (peer.alias.isEmpty ? formatID(peer.id) : peer.alias),", 2)
    # Keep existing layout/selection behavior; only replace the subtitle content.
    old = "'${peer.username}${peer.username.isNotEmpty && peer.hostname.isNotEmpty ? '@' : ''}${peer.hostname}'"
    change(old, "(isDesktop && [PeerTabIndex.group, PeerTabIndex.ab].contains(widget.tab) ? formatID(peer.id) : '${peer.username}${peer.username.isNotEmpty && peer.hostname.isNotEmpty ? '@' : ''}${peer.hostname}')", 2)
    change('final name = hideUsernameOnCard == true', 'final name = isDesktop && [PeerTabIndex.group, PeerTabIndex.ab].contains(widget.tab) ? formatID(peer.id) : hideUsernameOnCard == true', 2)
    source = "import '../../models/rdgen_device_organization_origin.dart';\n" + source
    path.write_text(source, encoding='utf-8')
    for name in ['device_menu', 'device_organization_origin']:
        (root/f'flutter/lib/models/rdgen_{name}.dart').write_text(Path(__file__).with_name(name+'.dart').read_text(encoding='utf-8'), encoding='utf-8')
    connection = root/'flutter/lib/desktop/pages/connection_page.dart'
    text = connection.read_text(encoding='utf-8')
    if text.count("translate('Ready')") != 1: raise ValueError('Incompatible ready status')
    connection.write_text(text.replace("translate('Ready')", "translate('Connected')"), encoding='utf-8')
