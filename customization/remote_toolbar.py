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

    source = "import '../../models/rdgen_compact_session_toolbar.dart';\n"+source
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
    change('    toolbarItems.add(_ChatMenu(id: widget.id, ffi: widget.ffi));', '''    final compact = widget.ffi.ffiModel.rdgenOrganization.supported;
    if (!compact) toolbarItems.add(_ChatMenu(id: widget.id, ffi: widget.ffi));''')
    change('    if (!isWeb) toolbarItems.add(_RecordMenu());', '''    if (!compact && !isWeb) toolbarItems.add(_RecordMenu());
    if (compact) {
      toolbarItems.insert(1, RdgenOrganizationToolbarButton(
        name: widget.ffi.ffiModel.rdgenOrganization.name,
        additionalCount: widget.ffi.ffiModel.rdgenOrganization.additionalCount,
        onPressed: () => widget.ffi.ffiModel.rdgenOrganization.choose(
          widget.ffi.dialogManager, () => !widget.ffi.closed)));
      toolbarItems.add(_IconSubmenuButton(tooltip: 'More',
        icon: const Icon(Icons.more_horiz, color: Colors.white, size: 20),
        color: _ToolbarTheme.inactiveColor, hoverColor: _ToolbarTheme.hoverInactiveColor,
        ffi: widget.ffi, menuChildrenGetter: (_) => [
          Row(mainAxisSize: MainAxisSize.min, children: [
            Padding(padding: const EdgeInsets.symmetric(horizontal: 8), child: Text(translate('Chat'))),
            _ChatMenu(id: widget.id, ffi: widget.ffi),
          ]),
          if (!isWeb) Row(mainAxisSize: MainAxisSize.min, children: [
            Padding(padding: const EdgeInsets.symmetric(horizontal: 8), child: Text(translate('Session recording'))),
            _RecordMenu(),
          ]),
        ]));
    }''')
    change('    final toolbarBorderRadius = BorderRadius.all(Radius.circular(4.0));', '''    if (compact) {
      return Material(color: const Color(0xff22252b), elevation: 4,
        borderRadius: const BorderRadius.vertical(bottom: Radius.circular(8)),
        child: SingleChildScrollView(scrollDirection: Axis.horizontal,
          child: Padding(padding: const EdgeInsets.symmetric(horizontal: 3, vertical: 2),
            child: Row(mainAxisSize: MainAxisSize.min, children: toolbarItems))));
    }
    final toolbarBorderRadius = BorderRadius.all(Radius.circular(4.0));''')
    change('        icon: monitorsIcon,', '''        icon: ffi.ffiModel.rdgenOrganization.supported
          ? SizedBox(width: 54, child: Obx(() => Row(mainAxisSize: MainAxisSize.min, children: [
              const Icon(Icons.desktop_windows_outlined, color: Colors.white, size: 16),
              const SizedBox(width: 3),
              Text('${pi.currentDisplay < 0 ? "*" : pi.currentDisplay + 1}/${ffi.ffiModel.pi.displaysCount.value}',
                style: const TextStyle(color: Colors.white, fontSize: 11)),
            ]))) : monitorsIcon,''')
    # Only rendering primitives are resized. Their callbacks and action-specific
    # permission/state checks above are untouched.
    start = source.index('class _IconMenuButtonState ')
    end = source.index('class _SubmenuButton ', start)
    prefix, body, suffix = source[:start], source[start:end], source[end:]
    for name, value in [('buttonSize', '28.0'), ('buttonHMargin', '1.0'), ('buttonVMargin', '1.0')]:
        body = body.replace('_ToolbarTheme.'+name,
            '(RdgenCompactToolbarScope.active(context) ? '+value+' : _ToolbarTheme.'+name+')')
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
    source = prefix+body+suffix
    # pi.currentDisplay is observed through the existing per-peer display state.
    source = source.replace('pi.currentDisplay < 0 ? "*" : pi.currentDisplay + 1',
        'CurrentDisplayState.find(id).value < 0 ? "*" : CurrentDisplayState.find(id).value + 1')
    path.write_text(source, encoding='utf-8')
    for name in ['compact_session_toolbar', 'session_organization', 'organization_choices']:
        (root/f'flutter/lib/models/rdgen_{name}.dart').write_text(
            Path(__file__).with_name(name+'.dart').read_text(encoding='utf-8'), encoding='utf-8')
