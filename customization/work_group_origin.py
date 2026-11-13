"""Pass an organization hint with one launch, including desktop window messages."""
from pathlib import Path
import re


def apply(root):
    edits = {}

    def read(name):
        return edits.get(name, (root/name).read_text(encoding='utf-8'))

    def change(name, old, new, count=1):
        text = read(name)
        if text.count(old) != count:
            raise ValueError('Incompatible organization launch hook: '+name+' '+old)
        edits[name] = text.replace(old, new)

    common = 'flutter/lib/common.dart'
    change(common, "import 'dart:async';", "import 'dart:async';\nimport 'models/rdgen_work_group_origin.dart';")
    change(common, "  if (id == '') return;", """  final organization = RdgenWorkGroupOrigin.read(context);
  if (organization != null && rdgenLaunchingWorkGroup != organization) {
    return runZoned(() => connect(context, id,
      isFileTransfer: isFileTransfer, isViewCamera: isViewCamera,
      isTerminal: isTerminal, isTcpTunneling: isTcpTunneling, isRDP: isRDP,
      forceRelay: forceRelay, password: password, connToken: connToken,
      isSharedPassword: isSharedPassword),
      zoneValues: {rdgenWorkGroupZoneKey: organization});
  }
  if (id == '') return;""")
    manager = 'flutter/lib/utils/multi_window_manager.dart'
    change(manager, "import 'dart:convert';", "import 'dart:convert';\nimport '../models/rdgen_work_group_origin.dart';")
    change(manager, '    final msg = jsonEncode(params);', """    if (rdgenLaunchingWorkGroup != null) {
      params['rdgen_work_group_id'] = rdgenLaunchingWorkGroup;
    }
    final msg = jsonEncode(params);""", 2)
    for kind in ['remote', 'file_manager', 'view_camera', 'port_forward', 'terminal']:
        page = f'flutter/lib/desktop/pages/{kind}_page.dart'
        text = read(page)
        text, n = re.subn(r'(?m)^(\s*)this.forceRelay', r'\1this.rdgenWorkGroupId,\n\1this.forceRelay', text, count=1)
        if n != 1 or text.count('  final bool? forceRelay;') != 1:
            raise ValueError('Incompatible organization page: '+kind)
        text = text.replace('  final bool? forceRelay;', '  final int? rdgenWorkGroupId;\n  final bool? forceRelay;', 1)
        if kind != 'terminal':
            text, n = re.subn(r'(_ffi = FFI\([^\n]+\);)', r'\1\n    _ffi.ffiModel.rdgenPreferredWorkGroupId = widget.rdgenWorkGroupId;', text, count=1)
            if n != 1: raise ValueError('Missing session initialization: '+kind)
        else:
            text = text.replace('      forceRelay: widget.forceRelay,', '      rdgenWorkGroupId: widget.rdgenWorkGroupId,\n      forceRelay: widget.forceRelay,', 1)
        edits[page] = text
        tab = f'flutter/lib/desktop/pages/{kind}_tab_page.dart'
        text = read(tab)
        for args in ['params', 'args']:
            pattern = r"(?m)^(\s*)forceRelay: "+args+r"\['forceRelay'\],"
            text, n = re.subn(pattern, lambda m: m[1]+f"rdgenWorkGroupId: {args}['rdgen_work_group_id'],\n"+m[0], text)
            if n != 1: raise ValueError('Missing window organization argument: '+tab+' '+args)
        if kind == 'terminal':
            text = text.replace('    bool? forceRelay,', '    int? rdgenWorkGroupId,\n    bool? forceRelay,', 1)
            text = text.replace('        forceRelay: forceRelay,', '        rdgenWorkGroupId: rdgenWorkGroupId,\n        forceRelay: forceRelay,', 1)
            text = text.replace('        forceRelay: page.forceRelay,', '        rdgenWorkGroupId: page.rdgenWorkGroupId,\n        forceRelay: page.forceRelay,', 1)
        edits[tab] = text
    terminal = 'flutter/lib/desktop/pages/terminal_connection_manager.dart'
    change(terminal, '    required bool? forceRelay,', '    int? rdgenWorkGroupId,\n    required bool? forceRelay,')
    change(terminal, '    final ffi = FFI(null);', '    final ffi = FFI(null);\n    ffi.ffiModel.rdgenPreferredWorkGroupId = rdgenWorkGroupId;')
    edits['flutter/lib/models/rdgen_work_group_origin.dart'] = Path(__file__).with_name('work_group_origin.dart').read_text(encoding='utf-8')
    for name, text in edits.items():
        (root/name).write_text(text, encoding='utf-8')
