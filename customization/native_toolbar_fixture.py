"""Use the generated upstream rendering widgets, without a native connection."""
from pathlib import Path
import subprocess


def native_toolbar_fixture(source, destination):
    def block(text, name):
        start = text.index('class ' + name + ' ')
        end = text.index('\n}', start) + 2
        return text[start:end]

    toolbar = (source / 'flutter/lib/desktop/widgets/remote_toolbar.dart').read_text(encoding='utf-8')
    common = (source / 'flutter/lib/common.dart').read_text(encoding='utf-8')
    fixture = """import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_svg/flutter_svg.dart';
import 'package:get/get.dart';
import '../lib/models/rdgen_compact_session_toolbar.dart';
import '../lib/models/rdgen_session_organization.dart';
import '../lib/models/rdgen_session_work_groups.dart';
import '../lib/models/rdgen_organization_toolbar.dart';
import '../lib/common.dart' show OverlayDialogManager;
const isWindows = true;
const isDesktop = true;
String translate(String key) => key;
// The rendering tests pass ffi=null: no permission, session or network mock runs.
class FFI { dynamic get ffiModel => throw UnimplementedError(); }
Widget _buildPointerTrackWidget(Widget child, FFI? ffi) => child;
"""
    fixture += block(common, 'ColorThemeExtension')
    fixture += """
class MyTheme {
  static const button = Color(0xff6750a4);
  static const accent = Color(0xff6750a4);
  static const border = Color(0xffcccccc);
  static ColorThemeExtension color(BuildContext context) =>
    Theme.of(context).extension<ColorThemeExtension>()!;
}
"""
    for name in ['_ToolbarTheme', '_IconMenuButton', '_IconMenuButtonState', '_IconSubmenuButton', '_IconSubmenuButtonState']:
        fixture += '\n' + block(toolbar, name)
    fixture += Path(__file__).with_name('native_toolbar_render_test.dart').read_text(encoding='utf-8')
    destination.write_text(fixture, encoding='utf-8')
