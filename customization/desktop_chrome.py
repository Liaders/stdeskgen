"""Small desktop-only branding and local-ID actions, independent of UI profiles."""
import re


def apply_flutter(root):
    common=root/'flutter/lib/common.dart'
    home=root/'flutter/lib/desktop/pages/desktop_home_page.dart'
    source=common.read_text(encoding='utf-8')
    old='Widget loadPowered(BuildContext context) {\n  if ('
    if source.count(old)!=1:raise ValueError('Incompatible powered-by widget')
    common_text=source.replace(old,old+'isDesktop || ',1)
    source=home.read_text(encoding='utf-8')
    if source.count('Icons.more_vert_outlined,')!=1:raise ValueError('Incompatible ID settings button')
    source=source.replace('Icons.more_vert_outlined,','Icons.build_outlined,',1)
    anchor='                          contentPadding: EdgeInsets.only(top: 10, bottom: 10),'
    if source.count(anchor)!=1:raise ValueError('Incompatible local ID field')
    button=r"""
                          suffixIconConstraints: const BoxConstraints.tightFor(width: 28, height: 28),
                          suffixIcon: IconButton(
                            tooltip: translate('Copy') + ' ID',
                            padding: EdgeInsets.zero,
                            constraints: const BoxConstraints.tightFor(width: 28, height: 28),
                            icon: const Icon(Icons.content_copy, size: 18),
                            onPressed: () async {
                              final id = model.serverId.text.replaceAll(RegExp(r'\s+'), '');
                              if (!RegExp(r'^\d+$').hasMatch(id)) return;
                              await Clipboard.setData(ClipboardData(text: id));
                              showToast(translate('Copied'));
                            },
                          ),"""
    source=source.replace(anchor,anchor+button,1)
    server=root/'flutter/lib/desktop/pages/server_page.dart'
    server_text=server.read_text(encoding='utf-8')
    accept='''                      color: MyTheme.accent,
                      onClick: () {
                        handleAccept(context);'''
    if server_text.count(accept)!=1:raise ValueError('Incompatible incoming connection accept button')
    server_text=server_text.replace(accept,accept.replace('MyTheme.accent','Colors.green[700]'),1)
    common.write_text(common_text,encoding='utf-8')
    home.write_text(source,encoding='utf-8')
    server.write_text(server_text,encoding='utf-8')


def apply_sciter(root):
    path=root/'src/ui/index.tis';source=path.read_text(encoding='utf-8')
    source,count=re.subn(r"^ *\{is_custom_client[^\n]*translate\('powered_by_me'\)[^\n]*\n",'',source,flags=re.M)
    if count!=1:raise ValueError('Incompatible Sciter powered-by caption')
    path.write_text(source,encoding='utf-8')
