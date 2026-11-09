"""StatusDesk mobile appearance, service labels and supplied Android launcher resources."""
import argparse
import html
import json
from pathlib import Path
import shutil
import xml.etree.ElementTree as ET
from apply_profile import apply as apply_profile

ICONS=Path(__file__).with_name('android_icons')


def apply_ui(root,version,name):
    apply_profile(root,version,{'schema_version':1,'accent':'#EF7F1A','button':'#EF7F1A','colleagues':True},desktop_navigation=False)
    path=root/'flutter/lib/common.dart';source=path.read_text(encoding='utf-8')
    anchor='Widget loadPowered(BuildContext context) {\n  if ('
    if source.count(anchor)!=1:raise ValueError('Incompatible Android powered-by widget')
    path.write_text(source.replace(anchor,anchor+'isAndroid || ',1),encoding='utf-8')
    # The light mobile header has its own theme; the ID field uses a separate
    # upstream blue constant instead of the application's accent.
    source=path.read_text(encoding='utf-8')
    light,dark=source.split('  static ThemeData darkTheme =',1)
    header='    appBarTheme: AppBarTheme(\n      shadowColor: Colors.transparent,\n    ),'
    if light.count(header)!=1:raise ValueError('Incompatible Android light header theme')
    light=light.replace(header,'    appBarTheme: AppBarTheme(\n      backgroundColor: isAndroid ? MyTheme.accent : null,\n      foregroundColor: isAndroid ? Colors.white : null,\n      shadowColor: Colors.transparent,\n    ),',1)
    path.write_text(light+'  static ThemeData darkTheme ='+dark,encoding='utf-8')
    path=root/'flutter/lib/mobile/pages/connection_page.dart';source=path.read_text(encoding='utf-8')
    style="""                        style: const TextStyle(
                          fontFamily: 'WorkSans',
                          fontWeight: FontWeight.bold,
                          fontSize: 30,
                          color: MyTheme.idColor,
                        ),"""
    if source.count(style)!=1:raise ValueError('Incompatible Android remote ID style')
    source=source.replace(style,style.replace('const TextStyle','TextStyle').replace('MyTheme.idColor','isAndroid ? MyTheme.accent : MyTheme.idColor'),1)
    path.write_text(source,encoding='utf-8')
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
