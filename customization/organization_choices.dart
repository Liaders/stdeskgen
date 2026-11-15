import 'package:flutter/material.dart';
import '../common.dart' show translate;

class RdgenOrganizationChoices extends StatefulWidget {
  final List<Map<String, dynamic>> groups;
  final int? selected;
  final int? origin;
  final bool busy;
  final bool showCreate;
  final ValueChanged<int?> onChanged;
  const RdgenOrganizationChoices({super.key, required this.groups,
    required this.selected, this.origin, this.busy = false, this.showCreate = true, required this.onChanged});
  @override
  State<RdgenOrganizationChoices> createState() => _RdgenOrganizationChoicesState();
}

class _RdgenOrganizationChoicesState extends State<RdgenOrganizationChoices> {
  String search = '';
  @override
  Widget build(BuildContext context) {
    final groups = widget.groups.where((g) =>
        (g['name'] as String).toLowerCase().contains(search.toLowerCase())).toList();
    return Column(mainAxisSize: MainAxisSize.min, children: [
      TextField(enabled: !widget.busy,
        decoration: InputDecoration(prefixIcon: const Icon(Icons.search),
          hintText: translate('Search organizations')),
        onChanged: (value) => setState(() { search = value; })),
      const SizedBox(height: 8),
      ConstrainedBox(constraints: const BoxConstraints(maxHeight: 280),
        child: SingleChildScrollView(child: Column(mainAxisSize: MainAxisSize.min,
          children: [
            if (groups.isEmpty) Text(translate('No organizations available')),
            ...groups.map((g) => RadioListTile<int>(value: g['id'] as int,
              groupValue: widget.selected, title: Text(g['name'] as String), dense: true,
              subtitle: g['id'] == widget.origin ? Text(translate('Selected from the current tab')) : null,
              onChanged: widget.busy ? null : widget.onChanged)),
          ]))),
      if (widget.showCreate) Tooltip(message: translate('Organization creation requires a server API update'),
        child: TextButton.icon(onPressed: null, icon: const Icon(Icons.add),
          label: Text(translate('Create organization…')))),
    ]);
  }
}
