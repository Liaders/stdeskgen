"""Expose the existing forget-password action in all Flutter device menus."""


def apply(root):
    path = root/'flutter/lib/common/widgets/peer_card.dart'
    source = path.read_text(encoding='utf-8')
    anchor = '          if (tab.index == PeerTabIndex.ab.index) {\n            BotToast.showText('
    if source.count(anchor) != 1: raise ValueError('Incompatible password error feedback')
    source = source.replace(anchor,
        '          if (tab.index == PeerTabIndex.ab.index && gFFI.abModel.current.isPersonal()) {\n            BotToast.showText(', 1)
    for name in ['DiscoveredPeerCard', 'AddressBookPeerCard', 'MyGroupPeerCard']:
        start = source.index('class '+name+' extends BasePeerCard {')
        end = source.find('\nclass ', start+1)
        if end < 0: end = len(source)
        body = source[start:end]
        anchor = '    return menuItems;'
        if body.count(anchor) != 1: raise ValueError('Incompatible password menu: '+name)
        condition = 'await bind.mainPeerHasPassword(id: peer.id)'
        if name == 'AddressBookPeerCard':
            condition += ' &&\n        !(gFFI.abModel.current.canWrite() && gFFI.abModel.current.isPersonal() && peer.hash.isNotEmpty)'
        addition = '    if ('+condition+') {\n      menuItems.add(_unrememberPasswordAction(peer.id));\n    }\n'
        body = body.replace(anchor, addition+anchor, 1)
        source = source[:start]+body+source[end:]
    path.write_text(source, encoding='utf-8')
