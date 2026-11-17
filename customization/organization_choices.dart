import 'package:flutter/material.dart';
import '../common.dart' show translate;

/// Bound choices select the session; search offers new device bindings only.
class RdgenOrganizationChoices extends StatelessWidget {
  final List<Map<String, dynamic>> groups;
  final List<Map<String, dynamic>> boundGroups;
  final int? selected;
  final int? origin;
  final bool busy;
  final bool showCreate; // Compatibility only: client creation is disabled.
  final ValueChanged<int?> onChanged;
  const RdgenOrganizationChoices({super.key, required this.groups,
    this.boundGroups = const [], required this.selected, this.origin,
    this.busy = false, this.showCreate = false, required this.onChanged});
  @override
  Widget build(BuildContext context) {
    final boundIds = boundGroups.map((g) => g['id']).toSet();
    return Column(mainAxisSize: MainAxisSize.min, children: [
      if (boundGroups.isNotEmpty) ConstrainedBox(constraints: const BoxConstraints(maxHeight: 210),
        child: SingleChildScrollView(child: Column(mainAxisSize: MainAxisSize.min,
          children: boundGroups.map((g) => RadioListTile<int>(value: g['id'] as int,
            groupValue: selected, dense: true, title: Text(g['name'] as String),
            subtitle: g['id'] == origin ? Text(translate('Selected from the current tab')) : null,
            onChanged: busy ? null : onChanged)).toList()))),
      const SizedBox(height: 8),
      RawAutocomplete<Map<String, dynamic>>(
        displayStringForOption: (g) => g['name'] as String,
        optionsBuilder: (value) {
          if (busy || value.text.trim().isEmpty) return const Iterable<Map<String, dynamic>>.empty();
          final query = value.text.trim().toLowerCase();
          return groups.where((g) => !boundIds.contains(g['id']) &&
            (g['name'] as String).toLowerCase().contains(query)).take(100);
        },
        onSelected: (g) => onChanged(g['id'] as int),
        fieldViewBuilder: (context, controller, focus, submit) => TextField(
          controller: controller, focusNode: focus, enabled: !busy,
          onChanged: (_) => onChanged(null),
          onSubmitted: (_) => submit(), decoration: InputDecoration(
            prefixIcon: const Icon(Icons.search), hintText: translate('Search organizations'))),
        optionsViewBuilder: (context, select, options) {
          final rows = options.toList();
          return Align(alignment: Alignment.topLeft, child: Material(elevation: 6,
            borderRadius: BorderRadius.circular(6),
            child: SizedBox(width: 396, height: (rows.length * 36.0).clamp(0.0, 216.0),
              child: ListView.builder(padding: EdgeInsets.zero, itemCount: rows.length,
                itemExtent: 36, itemBuilder: (context, index) => InkWell(
                  onTap: () => select(rows[index]), child: Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 12),
                    child: Align(alignment: Alignment.centerLeft,
                      child: Text(rows[index]['name'] as String, maxLines: 1,
                        overflow: TextOverflow.ellipsis))))))));
        }),
    ]);
  }
}
