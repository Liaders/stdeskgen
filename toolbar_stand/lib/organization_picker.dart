import 'package:flutter/material.dart';

class StandOrganizationChoice {
  final String name;
  final String? deviceAlias;
  const StandOrganizationChoice(this.name, {this.deviceAlias});
}

class StandOrganizationPicker extends StatefulWidget {
  final List<String> organizations, bindings;
  final String? current, deviceAlias;
  const StandOrganizationPicker(
      {super.key,
      required this.organizations,
      this.bindings = const [],
      this.current,
      this.deviceAlias});
  @override
  State<StandOrganizationPicker> createState() =>
      _StandOrganizationPickerState();
}

class _StandOrganizationPickerState extends State<StandOrganizationPicker> {
  late final alias = TextEditingController(text: widget.deviceAlias ?? '');
  late String? selected = widget.current;
  @override
  void dispose() {
    alias.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => AlertDialog(
          title: const Text('Выберите организацию'),
          content: SizedBox(
              width: 420,
              child: SingleChildScrollView(
                  child: Column(mainAxisSize: MainAxisSize.min, children: [
                TextField(
                    key: const ValueKey('device-alias'),
                    controller: alias,
                    maxLength: 255,
                    decoration: const InputDecoration(
                        labelText: 'Псевдоним устройства (необязательно)',
                        helperText:
                            'Для удобства навигации. Имя компьютера не меняется.',
                        helperMaxLines: 2)),
                ...widget.bindings.map((name) => RadioListTile<String>(
                    dense: true,
                    title: Text(name),
                    value: name,
                    groupValue: selected,
                    onChanged: (value) => setState(() => selected = value))),
                RawAutocomplete<String>(
                    optionsBuilder: (value) => value.text.trim().isEmpty
                        ? const []
                        : widget.organizations.where((name) =>
                            !widget.bindings.contains(name) &&
                            name
                                .toLowerCase()
                                .contains(value.text.toLowerCase())),
                    onSelected: (value) => setState(() => selected = value),
                    fieldViewBuilder: (context, controller, focus, submit) =>
                        TextField(
                            key: const ValueKey('organization-search'),
                            controller: controller,
                            focusNode: focus,
                            onChanged: (_) => setState(() => selected = null),
                            onSubmitted: (_) => submit(),
                            decoration: const InputDecoration(
                                prefixIcon: Icon(Icons.search),
                                hintText: 'Поиск организаций')),
                    optionsViewBuilder: (context, select, options) => Align(
                        alignment: Alignment.topLeft,
                        child: Material(
                            elevation: 6,
                            borderRadius: BorderRadius.circular(6),
                            child: SizedBox(
                                width: 396,
                                height:
                                    (options.length * 36.0).clamp(0.0, 216.0),
                                child: ListView(
                                    padding: EdgeInsets.zero,
                                    children: options
                                        .map((name) => InkWell(
                                            onTap: () => select(name),
                                            child: SizedBox(
                                                height: 36,
                                                child: Padding(
                                                    padding: const EdgeInsets.symmetric(horizontal: 12),
                                                    child: Align(alignment: Alignment.centerLeft, child: Text(name))))))
                                        .toList()))))),
              ]))),
          actions: [
            TextButton(
                onPressed: () => Navigator.pop(context),
                child: const Text('Отмена')),
            ElevatedButton(
                onPressed: selected == null
                    ? null
                    : () => Navigator.pop(
                        context,
                        StandOrganizationChoice(selected!,
                            deviceAlias: alias.text.trim())),
                child: const Text('Подтвердить')),
          ]);
}

class StandDeviceAliasDialog extends StatefulWidget {
  final String? current;
  const StandDeviceAliasDialog({super.key, this.current});
  @override
  State<StandDeviceAliasDialog> createState() => _StandDeviceAliasDialogState();
}

class _StandDeviceAliasDialogState extends State<StandDeviceAliasDialog> {
  late final controller = TextEditingController(text: widget.current ?? '');
  @override
  void dispose() {
    controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => AlertDialog(
          title: const Text('Изменить псевдоним устройства'),
          content: SizedBox(
              width: 420,
              child: TextField(
                  key: const ValueKey('standalone-device-alias'),
                  controller: controller,
                  maxLength: 255,
                  autofocus: true,
                  decoration: const InputDecoration(
                      labelText: 'Псевдоним устройства',
                      helperText:
                          'Для удобства навигации. Имя компьютера не меняется.',
                      helperMaxLines: 2))),
          actions: [
            TextButton(
                onPressed: () => Navigator.pop(context),
                child: const Text('Отмена')),
            ElevatedButton(
                onPressed: () => Navigator.pop(context, controller.text.trim()),
                child: const Text('Сохранить')),
          ]);
}
