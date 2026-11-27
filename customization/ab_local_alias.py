from pathlib import Path
import re

def add_ab_local_alias(root, edits):
    path=root/'flutter/lib/common/widgets/peer_card.dart'
    text=edits.get(path,path.read_text(encoding='utf-8'))
    text="import '../../models/rdgen_ab_local_alias.dart';\n"+text
    pattern=r'child: (Text\(\s*[^\n]*?(?:widget.tab == PeerTabIndex.group|rdgenServerDeviceName|peer.alias.isEmpty)[^\n]*,\s*overflow: TextOverflow.ellipsis,\s*style: Theme.of\(context\).textTheme.titleSmall,\s*\))'
    text,n=re.subn(pattern,lambda m:"child: isDesktop && widget.tab == PeerTabIndex.ab ? RdgenAbAliasLabel(id: peer.id, fallback: "+m[1]+") : "+m[1],text)
    if n!=2: raise ValueError('Incompatible address-book title anchors: '+str(n))
    start=text.index('class AddressBookPeerCard extends BasePeerCard {');end=text.index('\nclass MyGroupPeerCard',start)
    body=text[start:end]
    anchor='    return menuItems;'
    if body.count(anchor)!=1:raise ValueError('Incompatible address book menu')
    body=body.replace(anchor,'''    if (isDesktop) {
      final rename = menuItems.indexWhere((entry) => false);
      final localEntry = MenuEntryButton<String>(
        childBuilder: (style) => Text(translate('Local device alias'), style: style),
        proc: () => rdgenEditLocalAbAlias(context, peer.id), padding: menuPadding, dismissOnClicked: true);
      menuItems.add(localEntry);
    }
    return menuItems;''')
    # The desktop rename entry is the final append in our existing adapter.
    body=body.replace("    if (isDesktop) menuItems.add(_renameAction(context, peer.id));", "    if (isDesktop) menuItems.add(_renameAction(context, peer.id));")
    body=body.replace('      final rename = menuItems.indexWhere((entry) => false);\n','')
    text=text[:start]+body+text[end:]
    edits[path]=text
    edits[root/'flutter/lib/models/rdgen_ab_local_alias.dart']=Path(__file__).with_name('ab_local_alias.dart').read_text(encoding='utf-8-sig')
