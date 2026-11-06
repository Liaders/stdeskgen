"""StatusDesk mobile appearance, service labels and supplied Android launcher resources."""
import argparse
import html
import json
from pathlib import Path
import shutil
import xml.etree.ElementTree as ET
from apply_profile import apply as apply_profile
from colleagues import add_colleagues

ICONS=Path(__file__).with_name('android_icons')


def apply_ui(root,version,name):
    apply_profile(root,version,{'schema_version':1,'accent':'#EF7F1A','button':'#EF7F1A'})
    edits={}
    def replace(relative,old,new):
        path=root/relative;source=edits.get(path,path.read_text(encoding='utf-8'))
        if source.count(old)!=1:raise ValueError('Incompatible Android colleagues navigation: '+relative)
        edits[path]=source.replace(old,new,1)
    add_colleagues(root,edits,replace,{},standalone=True)
    page='flutter/lib/mobile/pages/home_page.dart'
    replace(page,"import 'connection_page.dart';","import 'connection_page.dart';\nimport 'rdgen_colleagues_page.dart';")
    replace(page,'    _pages.add(SettingsPage());', '''    _pages.add(SettingsPage());
    if (isAndroid && !bind.isIncomingOnly() &&
        !bind.isDisableGroupPanel() && !bind.isDisableAccount()) {
      _pages.add(RdgenColleaguesPage());
    }
    _selectedIndex = _selectedIndex.clamp(0, _pages.length - 1).toInt();''')
    replace(page,'BottomNavigationBarItem(icon: page.icon, label: page.title)', '''BottomNavigationBarItem(
                      icon: page.icon,
                      label: page is RdgenColleaguesPage ? '' : page.title,
                      tooltip: page is RdgenColleaguesPage ? page.title : null)''')
    replace(page,'  Widget appTitle() {', '''  Widget appTitle() {
    if (_pages[_selectedIndex] is RdgenColleaguesPage) {
      return Text(translate('Colleagues'));
    }''')
    edits[root/'flutter/lib/mobile/pages/rdgen_colleagues_page.dart']=Path(__file__).with_name('mobile_colleagues.dart').read_text(encoding='utf-8')
    for path,source in edits.items():path.write_text(source,encoding='utf-8')
    path=root/'flutter/lib/common.dart';source=path.read_text(encoding='utf-8')
    anchor='Widget loadPowered(BuildContext context) {\n  if ('
    if source.count(anchor)!=1:raise ValueError('Incompatible Android powered-by widget')
    path.write_text(source.replace(anchor,anchor+'isAndroid || ',1),encoding='utf-8')
    path=root/'flutter/lib/mobile/pages/settings_page.dart';source=path.read_text(encoding='utf-8')
    source=source.replace('https://rustdesk.com/privacy.html','https://status16.ru/')
    source=source.replace('https://rustdesk.com/','https://status16.ru/')
    source=source.replace("Text('rustdesk.com'","Text('status16.ru'")
    if 'rustdesk.com' in source:raise ValueError('Unchanged mobile website link')
    path.write_text(source,encoding='utf-8')
    path=root/'flutter/android/app/src/main/kotlin/com/carriez/flutter_hbb/MainService.kt';source=path.read_text(encoding='utf-8')
    for old,new in [('DEFAULT_NOTIFY_TITLE = "RustDesk"','DEFAULT_NOTIFY_TITLE = '+json.dumps(name)),
                    ('val channelName = "RustDesk Service"','val channelName = '+json.dumps(name)),
                    ('description = "RustDesk Service Channel"','description = '+json.dumps(name+' Service Channel'))]:
        if source.count(old)!=1:raise ValueError('Incompatible Android notification label: '+old)
        source=source.replace(old,new,1)
    source=source.replace('channel.lightColor = Color.BLUE','channel.lightColor = Color.rgb(239, 127, 26)')
    path.write_text(source,encoding='utf-8')
    for path in (root/'flutter/android/app/src/main/res').rglob('strings.xml'):
        path.write_text(path.read_text(encoding='utf-8').replace('RustDesk',html.escape(name,quote=True)),encoding='utf-8')
    path=root/'flutter/android/app/src/main/kotlin/com/carriez/flutter_hbb/BootReceiver.kt'
    path.write_text(path.read_text(encoding='utf-8').replace('"RustDesk is Open"',json.dumps(name+' is Open')),encoding='utf-8')
    path=root/'flutter/android/app/src/main/kotlin/com/carriez/flutter_hbb/FloatingWindowService.kt'
    path.write_text(path.read_text(encoding='utf-8').replace('translate("Show RustDesk")','translate("Show RustDesk").replace("RustDesk", '+json.dumps(name)+')'),encoding='utf-8')


def apply_launcher(root):
    resources=root/'flutter/android/app/src/main/res'
    # flutter_launcher_icons and the supplied bundle define the same color.
    for path in (resources/'values').glob('*.xml'):
        tree=ET.parse(path);node=tree.getroot();changed=False
        for item in list(node):
            if item.tag=='color' and item.get('name')=='ic_launcher_background':node.remove(item);changed=True
            elif item.tag=='color' and item.get('name')=='primary':item.text='#FFEF7F1A';changed=True
        if changed:
            if len(node):tree.write(path,encoding='utf-8',xml_declaration=True)
            else:path.unlink()
    for source in ICONS.rglob('*'):
        if source.is_file() and source.suffix in ('.png','.xml') and source.name!='app_icon.png':
            target=resources/source.relative_to(ICONS);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target)
    manifest=root/'flutter/android/app/src/main/AndroidManifest.xml';source=manifest.read_text(encoding='utf-8')
    if 'android:roundIcon=' not in source:
        anchor='android:icon="@mipmap/ic_launcher"'
        if source.count(anchor)!=1:raise ValueError('Missing Android launcher icon')
        source=source.replace(anchor,anchor+'\n        android:roundIcon="@mipmap/ic_launcher_round"',1)
    manifest.write_text(source,encoding='utf-8')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--source',type=Path,default=Path('.'));args=parser.parse_args()
    apply_launcher(args.source)
