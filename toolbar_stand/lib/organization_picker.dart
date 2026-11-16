import 'package:flutter/material.dart';

class StandOrganizationChoice {
  final String name;
  final bool created;
  final bool assign;
  final List<String> groups;
  final String? deviceAlias;
  const StandOrganizationChoice(this.name,
      {this.created = false,
      this.assign = true,
      this.groups = const [],
      this.deviceAlias});
}

class StandOrganizationPicker extends StatefulWidget {
  final List<String> organizations;
  final bool offerDeviceAlias;
  const StandOrganizationPicker(
      {super.key, required this.organizations, this.offerDeviceAlias = false});
  @override
  State<StandOrganizationPicker> createState() =>
      _StandOrganizationPickerState();
}

class _StandOrganizationPickerState extends State<StandOrganizationPicker> {
  final search = TextEditingController();
  final alias = TextEditingController();
  void select(StandOrganizationChoice choice) {
    Navigator.pop(
        context,
        StandOrganizationChoice(choice.name,
            created: choice.created,
            assign: choice.assign,
            groups: choice.groups,
            deviceAlias: widget.offerDeviceAlias && alias.text.trim().isNotEmpty
                ? alias.text.trim()
                : null));
  }

  @override
  void dispose() {
    search.dispose();
    alias.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final query = search.text.trim().toLowerCase();
    final filtered = widget.organizations
        .where((name) => name.toLowerCase().contains(query))
        .toList();
    return AlertDialog(
        title: const Text('Назначить организацию'),
        content: SizedBox(
            width: 460,
            height: widget.offerDeviceAlias ? 410 : 300,
            child: Column(children: [
              if (widget.offerDeviceAlias) ...[
                TextField(
                    key: const ValueKey('device-alias'),
                    controller: alias,
                    maxLength: 255,
                    decoration: const InputDecoration(
                        labelText: 'Псевдоним устройства (необязательно)',
                        helperText:
                            'Для удобства поиска и навигации. Имя компьютера не меняется.',
                        helperMaxLines: 2,
                        isDense: true,
                        counterText: '')),
                const SizedBox(height: 20),
              ],
              TextField(
                  key: const ValueKey('organization-search'),
                  controller: search,
                  autofocus: true,
                  onChanged: (_) => setState(() {}),
                  decoration: const InputDecoration(
                      labelText: 'Поиск организации',
                      prefixIcon: Icon(Icons.search),
                      isDense: true)),
              const SizedBox(height: 12),
              Expanded(
                  child: filtered.isEmpty
                      ? const Center(child: Text('Организации не найдены'))
                      : ListView.builder(
                          itemCount: filtered.length,
                          itemBuilder: (_, index) => ListTile(
                              dense: true,
                              title: Text(filtered[index],
                                  style: const TextStyle(
                                      fontWeight: FontWeight.w400)),
                              leading: const Icon(Icons.apartment_outlined,
                                  size: 20),
                              onTap: () => select(
                                  StandOrganizationChoice(filtered[index]))))),
              const Align(
                  alignment: Alignment.centerLeft,
                  child: Text('Демонстрация · без обращения к серверу',
                      style: TextStyle(fontSize: 12, color: Colors.grey))),
            ])),
        actions: [
          TextButton(
              onPressed: () => Navigator.pop(context),
              child: const Text('Отмена')),
          OutlinedButton.icon(
              key: const ValueKey('create-organization'),
              icon: const Icon(Icons.add, size: 18),
              label: const Text('Создать организацию'),
              onPressed: () async {
                final result = await showDialog<StandOrganizationChoice>(
                    context: context,
                    builder: (_) => StandCreateOrganization(
                        existing: widget.organizations,
                        initialName: search.text.trim()));
                if (context.mounted && result != null) {
                  select(result);
                }
              })
        ]);
  }
}

class StandCreateOrganization extends StatefulWidget {
  final List<String> existing;
  final String initialName;
  const StandCreateOrganization(
      {super.key, required this.existing, this.initialName = ''});
  @override
  State<StandCreateOrganization> createState() =>
      _StandCreateOrganizationState();
}

class _StandCreateOrganizationState extends State<StandCreateOrganization> {
  late final controller = TextEditingController(text: widget.initialName);
  final groups = <String>{'Статус'};
  String? error;
  @override
  void dispose() {
    controller.dispose();
    super.dispose();
  }

  void save({bool assign = true}) {
    final name = controller.text.trim();
    if (name.isEmpty ||
        widget.existing.any((e) => e.toLowerCase() == name.toLowerCase())) {
      setState(() => error = name.isEmpty
          ? 'Введите название'
          : 'Организация с таким названием уже есть');
      return;
    }
    Navigator.pop(
        context,
        StandOrganizationChoice(name,
            created: true, assign: assign, groups: groups.toList()));
  }

  @override
  Widget build(BuildContext context) => AlertDialog(
          title: const Text('Создать организацию'),
          content: SizedBox(
              width: 460,
              child: Column(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    TextField(
                        key: const ValueKey('new-organization-name'),
                        controller: controller,
                        autofocus: true,
                        maxLength: 255,
                        decoration: InputDecoration(
                            labelText: 'Название организации',
                            errorText: error),
                        onSubmitted: (_) => save()),
                    const SizedBox(height: 12),
                    const Text('Группы пользователей',
                        style: TextStyle(fontWeight: FontWeight.w400)),
                    CheckboxListTile(
                        contentPadding: EdgeInsets.zero,
                        dense: true,
                        controlAffinity: ListTileControlAffinity.leading,
                        title: const Text('Статус'),
                        subtitle: const Text(
                            'Группа текущего оператора · выбрана заранее'),
                        value: groups.contains('Статус'),
                        onChanged: (value) => setState(() {
                              if (value == true) {
                                groups.add('Статус');
                              } else {
                                groups.remove('Статус');
                              }
                            })),
                    const Text(
                        '«Создать» — только добавить в список. «Создать и назначить» — создать и запросить подтверждение назначения устройству.',
                        style: TextStyle(fontSize: 12, color: Colors.grey)),
                  ])),
          actions: [
            TextButton(
                onPressed: () => Navigator.pop(context),
                child: const Text('Отмена')),
            OutlinedButton(
                key: const ValueKey('create-only-organization'),
                onPressed: () => save(assign: false),
                child: const Text('Создать')),
            ElevatedButton(
                key: const ValueKey('confirm-create-organization'),
                onPressed: () => save(),
                child: const Text('Создать и назначить'))
          ]);
}

class StandDeviceAliasDialog extends StatefulWidget {
  const StandDeviceAliasDialog({super.key});
  @override
  State<StandDeviceAliasDialog> createState() => _StandDeviceAliasDialogState();
}

class _StandDeviceAliasDialogState extends State<StandDeviceAliasDialog> {
  final controller = TextEditingController();
  String? error;
  @override
  void dispose() {
    controller.dispose();
    super.dispose();
  }

  void save() {
    final value = controller.text.trim();
    if (value.isEmpty) {
      setState(() => error = 'Введите псевдоним');
      return;
    }
    Navigator.pop(context, value);
  }

  @override
  Widget build(BuildContext context) => AlertDialog(
          title: const Text('Назначить псевдоним устройства'),
          content: SizedBox(
              width: 460,
              child: TextField(
                  key: const ValueKey('standalone-device-alias'),
                  controller: controller,
                  autofocus: true,
                  maxLength: 255,
                  onSubmitted: (_) => save(),
                  decoration: InputDecoration(
                      labelText: 'Псевдоним устройства',
                      errorText: error,
                      helperText:
                          'Для удобства поиска и навигации. Имя компьютера не меняется.',
                      helperMaxLines: 2))),
          actions: [
            TextButton(
                onPressed: () => Navigator.pop(context),
                child: const Text('Отмена')),
            ElevatedButton(onPressed: save, child: const Text('Сохранить'))
          ]);
}
