"""Opt-in winter decoration confined to the Flutter desktop home sidebar."""
import json
from pathlib import Path
import shutil


def apply(root):
    edits = {}

    def replace(name, old, new):
        path = root / name
        text = edits.get(path, path.read_text(encoding='utf-8'))
        if text.count(old) != 1:
            raise ValueError('Incompatible winter sidebar anchor: ' + name + ': ' + old)
        edits[path] = text.replace(old, new, 1)

    home = 'flutter/lib/desktop/pages/desktop_home_page.dart'
    replace(home, "import 'dart:async';",
            "import 'dart:async';\nimport '../../models/rdgen_winter_mode.dart';")
    replace(home, '        buildLeftPane(context),',
            '        RdgenWinterPane(builder: buildLeftPane),')
    replace(home, '        child: loadLogo(),',
            '        child: rdgenWinterMode.value ? const RdgenWinterLogo() : loadLogo(),')
    # Keep the existing controls and their event handlers above the new scene.
    path = root / home
    source = edits[path]
    start = source.index('        child: Stack(', source.index('  Widget buildLeftPane('))
    begin = start + len('        child: ')
    end = _closing_parenthesis(source, begin + len('Stack')) + 1
    stack = source[begin:end]
    source = source[:begin] + ('rdgenWinterPanel(contentKey: _childKey, '
        'scrollController: _leftPaneScrollController, child: ' + stack + ')') + source[end:]
    edits[path] = source
    replace(home, '                SingleChildScrollView(',
            '                rdgenWinterScroll(SingleChildScrollView(')
    replace(home, '                  child: Column(\n                    key: _childKey,',
            '                  child: rdgenWinterObserve(Column(\n                    key: _childKey,')
    replace(home, '                    children: children,\n                  ),\n                ),',
            '                    children: children,\n                  )),\n                )),')
    replace(home, '                Expanded(child: Container())',
            '                if (!rdgenWinterMode.value) Expanded(child: Container())')

    settings = 'flutter/lib/desktop/pages/desktop_setting_page.dart'
    replace(settings, "import 'package:flutter/material.dart';",
            "import 'package:flutter/material.dart';\nimport '../../models/rdgen_winter_mode.dart';")
    replace(settings, "      _Card(title: 'Interface', children: [", """      _Card(title: 'Interface', children: [
        _Checkbox(label: 'New Year mode',
          getValue: () => rdgenWinterMode.value,
          setValue: setRdgenWinterMode),""")

    for path in (root / 'src/lang').glob('*.rs'):
        if path.name == 'en.rs':
            continue
        text = path.read_text(encoding='utf-8')
        anchor = '    ].iter().cloned().collect();'
        if text.count(anchor) != 1:
            raise ValueError('Incompatible winter translation: ' + path.name)
        prefix, suffix = text.split(anchor)
        label = 'Новогодний режим' if path.name == 'ru.rs' else ''
        entry = json.dumps(label, ensure_ascii=False)
        edits[path] = prefix.rstrip().removesuffix(',') + ',\n        ("New Year mode", ' + entry + '),\n' + anchor + suffix

    directory = Path(__file__).parent
    edits[root / 'flutter/lib/models/rdgen_winter_mode.dart'] = (
        directory / 'winter_mode.dart').read_text(encoding='utf-8')
    edits[root / 'flutter/lib/models/rdgen_winter_scene.dart'] = (
        directory / 'winter_scene.dart').read_text(encoding='utf-8')
    for path, text in edits.items():
        path.write_text(text, encoding='utf-8')
    destination = root / 'flutter/assets'
    destination.mkdir(parents=True, exist_ok=True)
    for asset in (directory / 'winter_assets').glob('*.png'):
        shutil.copyfile(asset, destination / asset.name)


def _closing_parenthesis(text, opening):
    depth = 0
    for position in range(opening, len(text)):
        if text[position] == '(':
            depth += 1
        elif text[position] == ')':
            depth -= 1
            if depth == 0:
                return position
    raise ValueError('Unbalanced desktop sidebar stack')
