"""Compact supported-server toolbar; upstream action widgets remain authoritative."""
from pathlib import Path


def apply(root):
    path = root/'flutter/lib/desktop/widgets/remote_toolbar.dart'
    source = path.read_text(encoding='utf-8')

    def change(old, new, count=1):
        nonlocal source
        if source.count(old) != count:
            raise ValueError('Incompatible compact session toolbar: '+old[:100])
        source = source.replace(old, new)

    source = "import '../../models/rdgen_compact_session_toolbar.dart';\nimport '../../models/rdgen_organization_toolbar.dart';\nimport '../../utils/multi_window_manager.dart';\n"+source
    change('    if (!pin && collapse.isFalse && _isCursorOverImage && _dragging.isFalse) {',
           '''    if (!pin && !widget.ffi.ffiModel.rdgenOrganization.interacting &&
        (!widget.ffi.ffiModel.rdgenOrganization.supported ||
          (!widget.ffi.dialogManager.rdgenHasOpenDialogs && !gFFI.dialogManager.rdgenHasOpenDialogs)) &&
        collapse.isFalse && _isCursorOverImage && _dragging.isFalse) {''')
    start = source.index('class _RemoteToolbarState ')
    end = source.index('  Widget _buildDragPreview(', start)
    prefix, body, suffix = source[:start], source[start:end], source[end:]
    anchor = '  Widget build(BuildContext context) {\n    return Obx(() {'
    if body.count(anchor) != 1: raise ValueError('Incompatible toolbar build')
    body = body.replace(anchor, '''  Widget build(BuildContext context) {
    final organization = widget.ffi.ffiModel.rdgenOrganization;
    return ListenableBuilder(listenable: organization, builder: (context, _) => Obx(() {''', 1)
    anchor = '      // If toolbar is hidden, return empty widget'
    if body.count(anchor) != 1: raise ValueError('Incompatible toolbar visibility')
    body = body.replace(anchor, '''      if (organization.supported) {
        return RdgenCompactSessionToolbar(
          collapsed: !pin && (collapse.value || hide.value),
          assigned: organization.assigned, organization: organization.name,
          onExpand: () {
            if (hide.value) widget.state.switchHide(widget.ffi.sessionId);
            if (collapse.value) widget.state.switchCollapse(widget.ffi.sessionId);
            triggerAutoHide();
          },
          onChoose: () => organization.choose(widget.ffi.dialogManager,
            () => !widget.ffi.closed),
          child: _buildToolbar(context, _ToolbarEdge.top, true));
      }
'''+anchor, 1)
    anchor = '    });\n  }\n\n'
    if not body.endswith(anchor): raise ValueError('Incompatible toolbar build end')
    body = body[:-len(anchor)]+'    }));\n  }\n\n'
    source = prefix+body+suffix
    change('    final List<Widget> toolbarItems = [];',
        '    final compact = widget.ffi.ffiModel.rdgenOrganization.supported;\n    final List<Widget> toolbarItems = [];')
    if 'mainGetLocalBoolOptionSync(kOptionAllowMonitorSwitchMainToolbar)' in source:
        source = source.replace('mainGetLocalBoolOptionSync(kOptionAllowMonitorSwitchMainToolbar)',
            '!widget.ffi.ffiModel.rdgenOrganization.supported && mainGetLocalBoolOptionSync(kOptionAllowMonitorSwitchMainToolbar)', 1)
    change('    toolbarItems\n        .add(_ControlMenu(id: widget.id, ffi: widget.ffi, state: widget.state));',
        '    if (!compact) toolbarItems.add(_ControlMenu(id: widget.id, ffi: widget.ffi, state: widget.state));')
    change('    toolbarItems.add(_ChatMenu(id: widget.id, ffi: widget.ffi));', '''    if (compact) {
      toolbarItems.insert(2, _IconMenuButton(icon: const RdgenToolbarGlyph('fullscreen'), tooltip: 'Fullscreen',
        color: _ToolbarTheme.inactiveColor, hoverColor: _ToolbarTheme.hoverInactiveColor,
        onPressed: () => _setFullscreen(!stateGlobal.fullscreen.value)));
      toolbarItems.add(_ControlMenu(id: widget.id, ffi: widget.ffi, state: widget.state));
    }
    if (!compact) toolbarItems.add(_ChatMenu(id: widget.id, ffi: widget.ffi));''')
    change('      toolbarItems.add(_VoiceCallMenu(id: widget.id, ffi: widget.ffi));',
        '      if (!compact) toolbarItems.add(_VoiceCallMenu(id: widget.id, ffi: widget.ffi));')
    change('    if (!isWeb) toolbarItems.add(_RecordMenu());', '''    if (!compact && !isWeb) toolbarItems.add(_RecordMenu());
    if (compact) {
      Future<void> reopen(int group) async {
        if (!bind.willSessionCloseCloseSession(sessionId: widget.ffi.sessionId)) {
          throw StateError('Other display windows are still open');
        }
        final result = await rustDeskWinManager.call(WindowType.Main,
          'rdgen-new-organization-session', {'id': widget.id, 'group_id': group});
        if (result.result is! int || result.result < 0) throw StateError('New session window unavailable');
        closeConnection(id: widget.id);
      }
      toolbarItems.add(Container(width: 1, height: 22, margin: const EdgeInsets.symmetric(horizontal: 2.5), color: const Color(0xff4a4e53)));
      toolbarItems.add(Padding(padding: const EdgeInsets.symmetric(horizontal: 2.5), child: RdgenOrganizationSessionMenu(
        organization: widget.ffi.ffiModel.rdgenOrganization, manager: widget.ffi.dialogManager,
        current: () => !widget.ffi.closed,
        restart: bind.willSessionCloseCloseSession(sessionId: widget.ffi.sessionId) ? reopen : null)));
      toolbarItems.add(_IconSubmenuButton(tooltip: 'More',
        icon: const Icon(Icons.more_horiz, color: Colors.white, size: 20),
        color: _ToolbarTheme.inactiveColor, hoverColor: _ToolbarTheme.hoverInactiveColor,
        ffi: widget.ffi, menuChildrenGetter: (_) => [
          Row(mainAxisSize: MainAxisSize.min, children: [
            Padding(padding: const EdgeInsets.symmetric(horizontal: 8), child: Text(translate('Chat'))),
            _ChatMenu(id: widget.id, ffi: widget.ffi),
          ]),
          if (!isWeb) Row(mainAxisSize: MainAxisSize.min, children: [
            Padding(padding: const EdgeInsets.symmetric(horizontal: 8), child: Text(translate('Voice call'))),
            _VoiceCallMenu(id: widget.id, ffi: widget.ffi),
          ]),
          if (!isWeb) Row(mainAxisSize: MainAxisSize.min, children: [
            Padding(padding: const EdgeInsets.symmetric(horizontal: 8), child: Text(translate('Session recording'))),
            _RecordMenu(),
          ]),
        ]));
    }''')
    change('    toolbarItems.add(_CloseMenu(id: widget.id, ffi: widget.ffi));',
        '    if (!compact) toolbarItems.add(_CloseMenu(id: widget.id, ffi: widget.ffi));')
    change('    final toolbarBorderRadius = BorderRadius.all(Radius.circular(4.0));', '''    if (compact) {
      toolbarItems.add(_CloseMenu(id: widget.id, ffi: widget.ffi));
      return Material(color: const Color(0xff22252b), elevation: 4,
        borderRadius: const BorderRadius.vertical(bottom: Radius.circular(8)),
        child: SingleChildScrollView(scrollDirection: Axis.horizontal,
          child: Padding(padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 5),
            child: Row(mainAxisSize: MainAxisSize.min, children: toolbarItems))));
    }
    final toolbarBorderRadius = BorderRadius.all(Radius.circular(4.0));''')
    change('        icon: monitorsIcon,', '''        icon: ffi.ffiModel.rdgenOrganization.supported
          ? Obx(() => RdgenDisplayCounter(current: CurrentDisplayState.find(id).value,
              total: ffi.ffiModel.pi.displaysCount.value)) : monitorsIcon,''')
    change('        width: width.value,\n        color: _ToolbarTheme.blueColor,',
           '        width: ffi.ffiModel.rdgenOrganization.supported ? 84 : width.value,\n        color: _ToolbarTheme.blueColor,')
    # Only rendering primitives are resized. Their callbacks and action-specific
    # permission/state checks above are untouched.
    start = source.index('class _IconMenuButtonState ')
    end = source.index('class _SubmenuButton ', start)
    prefix, body, suffix = source[:start], source[start:end], source[end:]
    for name, value in [('buttonSize', '30.0'), ('buttonHMargin', '2.5'), ('buttonVMargin', '0.0')]:
        body = body.replace('_ToolbarTheme.'+name,
            '(RdgenCompactToolbarScope.active(context) ? '+value+' : _ToolbarTheme.'+name+')')
    body = body.replace('color: hover ? widget.hoverColor : widget.color,', """color: RdgenCompactToolbarScope.active(context)
                        ? (widget.tooltip == 'Close' ? const Color(0xffe44e49)
                          : widget.tooltip == 'Select Monitor' ? const Color(0xff21464b)
                          : hover ? const Color(0xff3b414b) : Colors.transparent)
                        : hover ? widget.hoverColor : widget.color,""")
    anchor = '        child: SubmenuButton(\n'
    if body.count(anchor) != 1: raise ValueError('Incompatible toolbar submenu lifecycle')
    body = body.replace(anchor, anchor+'''            onOpen: () {
              final organization = widget.ffi?.ffiModel.rdgenOrganization;
              if (organization != null && organization.supported) organization.menuDepth++;
            },
            onClose: () {
              final organization = widget.ffi?.ffiModel.rdgenOrganization;
              if (organization != null && organization.menuDepth > 0) organization.menuDepth--;
            },
''', 1)
    body = body.replace('BorderRadius.circular(_ToolbarTheme.iconRadius)',
        'BorderRadius.circular(RdgenCompactToolbarScope.active(context) ? 4 : _ToolbarTheme.iconRadius)')
    body = body.replace('    final icon = widget.icon ??', """    final compact = RdgenCompactToolbarScope.active(context);
    final glyph = switch (widget.tooltip) {
      'Pin Toolbar' || 'Unpin Toolbar' => 'pin', 'Close' => 'close',
      'Control Actions' => 'bolt', 'Display Settings' => 'settings',
      'Keyboard Settings' => 'keyboard', 'More' => 'more', _ => null,
    };
    final icon = compact && glyph != null ? Center(child: RdgenToolbarGlyph(glyph, color: widget.tooltip == 'Unpin Toolbar' ? const Color(0xffef7f1a) : Colors.white)) : widget.icon ??""")
    source = prefix+body+suffix
    # pi.currentDisplay is observed through the existing per-peer display state.
    source = source.replace('pi.currentDisplay < 0 ? "*" : pi.currentDisplay + 1',
        'CurrentDisplayState.find(id).value < 0 ? "*" : CurrentDisplayState.find(id).value + 1')
    path.write_text(source, encoding='utf-8')
    for name in ['compact_session_toolbar', 'session_organization', 'organization_choices', 'organization_toolbar']:
        (root/f'flutter/lib/models/rdgen_{name}.dart').write_text(
            Path(__file__).with_name(name+'.dart').read_text(encoding='utf-8'), encoding='utf-8')
