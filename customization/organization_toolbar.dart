import 'package:flutter/material.dart';
import '../common.dart' show OverlayDialogManager, translate;
import 'rdgen_compact_session_toolbar.dart';
import 'rdgen_session_organization.dart';

class RdgenOrganizationSessionMenu extends StatelessWidget {
  final RdgenSessionOrganization organization;
  final OverlayDialogManager manager;
  final bool Function() current;
  final Future<void> Function(int)? restart;
  const RdgenOrganizationSessionMenu({super.key, required this.organization,
    required this.manager, required this.current, this.restart});
  @override
  Widget build(BuildContext context) {
    final bindings = organization.api?.bindings ?? [];
    if (bindings.isEmpty) return RdgenOrganizationToolbarButton(name: organization.name,
      onPressed: () => organization.choose(manager, current, restart: restart));
    return MenuAnchor(style: rdgenCompactMenuStyle,
      onOpen: () { organization.menuDepth++; },
      onClose: () { if (organization.menuDepth > 0) organization.menuDepth--; },
      menuChildren: [
        if (!organization.assigned) MenuItemButton(style: rdgenCompactMenuButtonStyle,
          child: Text(translate('Organization not selected'))),
        for (final group in bindings) MenuItemButton(style: rdgenCompactMenuButtonStyle,
          leadingIcon: SizedBox(width: 18, child: organization.snapshot?['group']?['id'] == group['id']
            ? const Icon(Icons.check, size: 17) : null),
          onPressed: organization.assigned && restart == null && organization.snapshot?['group']?['id'] != group['id'] ? null
            : () => organization.switchOrganization(manager, current, group['id'] as int, restart),
          child: ConstrainedBox(constraints: const BoxConstraints(maxWidth: 380),
            child: Text(group['name'] as String, maxLines: 1, overflow: TextOverflow.ellipsis))),
        const Divider(height: 9, thickness: 1),
        MenuItemButton(style: rdgenCompactMenuButtonStyle,
          onPressed: () => organization.choose(manager, current, restart: restart),
          child: Text(translate('Assign organization'))),
        if (organization.canAssignAlias) MenuItemButton(style: rdgenCompactMenuButtonStyle,
          onPressed: () => organization.assignAlias(manager), child: Text(translate('Assign device alias'))),
        if (organization.assigned && restart == null) MenuItemButton(style: rdgenCompactMenuButtonStyle,
          child: Text(translate('Close other display windows before changing the session organization'))),
      ], builder: (_, controller, __) => RdgenOrganizationToolbarButton(name: organization.name,
        onPressed: () { if (controller.isOpen) { controller.close(); } else { controller.open(); } }));
  }
}
