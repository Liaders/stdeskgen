"""Add a desktop-only, locally remembered text/icon tab switch."""
import json


def add_navigation(root, edits, replace, initial):
    page = 'flutter/lib/common/widgets/peer_tab_page.dart'
    replace(page, '    with SingleTickerProviderStateMixin {',
            '    with SingleTickerProviderStateMixin {\n  bool _rdgenTextTabs = ' +
            ('true' if initial == 'text' else 'false') + ';')
    replace(page, '  _PeerTabPageState() {', '''  _PeerTabPageState() {
    if (isDesktop) {
      final saved = bind.getLocalFlutterOption(k: 'rdgen-navigation-style-v1');
      if (saved == 'text' || saved == 'icons') _rdgenTextTabs = saved == 'text';
    }''')
    replace(page, 'physics: NeverScrollableScrollPhysics(),',
            'physics: isDesktop && _rdgenTextTabs\n            ? ClampingScrollPhysics() : NeverScrollableScrollPhysics(),')
    replace(page, 'child: Icon(model.tabIcon(t), color: color)',
            '''child: (isDesktop && _rdgenTextTabs
                            ? Transform.translate(offset: const Offset(0, 5),
                                child: Text(model.tabTooltip(t), style: TextStyle(color: color)))
                            : Icon(model.tabIcon(t), color: color))''')
    replace(page, '      _createPeerViewTypeSwitch(context),', '''      if (isDesktop) _rdgenNavigationSwitch(),
      _createPeerViewTypeSwitch(context),''')
    replace(page, '  Widget _createPeerViewTypeSwitch(BuildContext context) {', '''  Widget _rdgenNavigationSwitch() {
    final label = translate(_rdgenTextTabs ? 'Show tab icons' : 'Show tab text');
    return Semantics(
      button: true,
      label: label,
      child: _hoverAction(
        context: context,
        toolTip: label,
        child: Icon(_rdgenTextTabs ? Icons.apps_rounded : Icons.text_fields_rounded, size: 18),
        onTap: () async {
          final value = !_rdgenTextTabs;
          setState(() => _rdgenTextTabs = value);
          await bind.setLocalFlutterOption(
              k: 'rdgen-navigation-style-v1', v: value ? 'text' : 'icons');
        }),
    );
  }

  Widget _createPeerViewTypeSwitch(BuildContext context) {''')
    translations = {'Show tab icons': 'Показывать значки вкладок',
                    'Show tab text': 'Показывать текст вкладок'}
    for path in (root/'src/lang').glob('*.rs'):
        if path.name == 'en.rs':
            continue  # These English keys are already the display strings.
        source = edits.get(path, path.read_text(encoding='utf-8'))
        missing = [key for key in translations if '"'+key+'"' not in source]
        if not missing:
            continue
        anchor = '    ].iter().cloned().collect();'
        if source.count(anchor) != 1:
            raise ValueError('Incompatible navigation translations: '+path.name)
        prefix, suffix = source.split(anchor)
        prefix = prefix.rstrip()
        if not prefix.endswith(','):
            prefix += ','
        entries = ''.join('\n        ('+json.dumps(key)+', '+
                          json.dumps(translations[key] if path.name == 'ru.rs' else '', ensure_ascii=False)+'),'
                          for key in missing)
        edits[path] = prefix+entries+'\n'+anchor+suffix
