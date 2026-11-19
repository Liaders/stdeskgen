import 'dart:async';
import 'organization_picker.dart';
import 'package:flutter/material.dart';
import 'models/rdgen_compact_session_toolbar.dart';
import 'stand_icons.dart';

const standMenuItemStyle = ButtonStyle(
  textStyle: WidgetStatePropertyAll(TextStyle(
      fontFamily: 'Roboto',
      fontSize: 13,
      height: 1.2,
      fontWeight: FontWeight.w400)),
  minimumSize: WidgetStatePropertyAll(Size(0, 28)),
  maximumSize: WidgetStatePropertyAll(Size(double.infinity, 28)),
  padding: WidgetStatePropertyAll(EdgeInsets.symmetric(horizontal: 10)),
  visualDensity: VisualDensity.standard,
  tapTargetSize: MaterialTapTargetSize.shrinkWrap,
);

void main() => runApp(const ToolbarStand());

class ToolbarStand extends StatelessWidget {
  const ToolbarStand({super.key});
  @override
  Widget build(BuildContext context) => MaterialApp(
      title: 'StatusDesk — стенд панели',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
          colorScheme: ColorScheme.fromSeed(seedColor: const Color(0xffef7f1a)),
          useMaterial3: false),
      home: const StandPage());
}

class StandPage extends StatefulWidget {
  const StandPage({super.key});
  @override
  State<StandPage> createState() => _StandPageState();
}

class _StandPageState extends State<StandPage> {
  bool collapsed = false, pinned = true, recording = false, dark = true;
  bool controls = true, svgIcons = true;
  Color get ink => dark ? Colors.white : const Color(0xff24272c);
  int total = 3, current = 0, menuDepth = 0;
  String? organization = 'Организация Статус';
  final List<String> bindings = ['Организация Статус', 'Узорметалл'];
  int session = 1;
  String? deviceAlias;
  String event = 'Стенд готов. Подключение к серверу не выполняется.';
  Timer? timer;
  final Map<String, String> selections = {};
  final Map<String, bool> toggles = {};
  final organizations = [
    'Организация Статус',
    'Узорметалл',
    'Организация с очень длинным названием для проверки панели'
  ];

  @override
  void dispose() {
    timer?.cancel();
    super.dispose();
  }

  void log(String value) => setState(() => event = value);
  void scheduleHide() {
    timer?.cancel();
    if (!pinned && menuDepth == 0) {
      timer = Timer(const Duration(seconds: 2), () {
        if (mounted && !pinned && menuDepth == 0) {
          setState(() => collapsed = true);
        }
      });
    }
  }

  Future<void> choose() async {
    menuOpened();
    final selection = await showDialog<StandOrganizationChoice>(
        context: context,
        builder: (_) => StandOrganizationPicker(
            organizations: List.of(organizations),
            bindings: List.of(bindings),
            current: organization,
            deviceAlias: deviceAlias));
    if (!mounted) return;
    if (selection != null) {
      final accepted = await activateOrganization(selection.name);
      if (mounted && accepted && selection.deviceAlias != null) {
        setState(() => deviceAlias = selection.deviceAlias);
      }
    }
    if (mounted) menuClosed();
  }

  Future<bool> activateOrganization(String name,
      {List<String> groups = const []}) async {
    if (name == organization) return true;
    menuOpened();
    final reconnect = organization != null;
    if (!reconnect && bindings.contains(name)) {
      setState(() {
        organization = name;
        event = 'Демонстрация: выбрана организация $name';
      });
      menuClosed();
      return true;
    }
    final accepted = await showDialog<bool>(
            context: context,
            builder: (context) => AlertDialog(
                    title: Text(reconnect
                        ? 'Переподключиться к этому устройству по другой организации?'
                        : 'Назначить организацию устройству?'),
                    content: Text(reconnect
                        ? 'Вы уверены, что хотите назначить организацию «$name»? Текущий сеанс будет завершён. Новый сеанс будет учитываться за этой организацией.'
                        : 'Вы уверены, что хотите назначить организацию «$name» этому устройству? Текущий сеанс будет учитываться за этой организацией.'),
                    actions: [
                      TextButton(
                          onPressed: () => Navigator.pop(context, false),
                          child: const Text('Отмена')),
                      ElevatedButton(
                          onPressed: () => Navigator.pop(context, true),
                          child: Text(
                              reconnect ? 'Переподключиться' : 'Назначить'))
                    ])) ??
        false;
    if (!mounted) return false;
    if (accepted) {
      setState(() {
        if (!bindings.contains(name)) bindings.add(name);
        if (reconnect) session++;
        organization = name;
        event =
            'Демонстрация: сеанс №$session — $name${groups.isEmpty ? "" : " · группы: ${groups.join(", ")}"}';
      });
    } else {
      log('Назначение отменено. Привязки устройства и организация сеанса не изменены.');
    }
    menuClosed();
    return accepted;
  }

  Future<void> assignAlias() async {
    menuOpened();
    final alias = await showDialog<String>(
        context: context,
        builder: (_) => StandDeviceAliasDialog(current: deviceAlias));
    if (!mounted) return;
    if (alias != null) {
      setState(() {
        deviceAlias = alias;
        event = 'Демонстрация: псевдоним устройства — $alias';
      });
    }
    menuClosed();
  }

  Widget action(IconData icon, String label, VoidCallback click,
          {Color? color}) =>
      Tooltip(
          message: label,
          child: SizedBox(
              width: 30,
              height: 30,
              child: TextButton(
                  onPressed: click,
                  style: rdgenToolbarButtonStyle(
                          foreground: ink,
                          background: icon == Icons.close
                              ? const Color(0xffe44e49)
                              : Colors.transparent)
                      .copyWith(
                          padding:
                              const WidgetStatePropertyAll(EdgeInsets.zero)),
                  child: RdgenToolbarGlyph(
                      icon == Icons.close
                          ? 'close'
                          : icon == Icons.keyboard_arrow_up
                              ? 'up'
                              : icon == Icons.bolt_outlined
                                  ? 'bolt'
                                  : icon == Icons.keyboard_outlined
                                      ? 'keyboard'
                                      : icon == Icons.settings_outlined
                                          ? 'settings'
                                          : icon == Icons.mouse_outlined
                                              ? 'fullscreen'
                                              : 'pin',
                      color: color ??
                          (icon == Icons.close ? Colors.white : ink)))));

  Widget separator() => Container(
      width: 1,
      height: 22,
      margin: EdgeInsets.zero,
      color: const Color(0xff4a4e53));
  void menuOpened() {
    timer?.cancel();
    menuDepth++;
  }

  void menuClosed() {
    if (menuDepth > 0) menuDepth--;
    scheduleHide();
  }

  Widget item(String label, {VoidCallback? onPressed, bool enabled = true}) =>
      MenuItemButton(
          style: standMenuItemStyle,
          onPressed:
              enabled ? (onPressed ?? () => log('Демонстрация: $label')) : null,
          child: Text(label));
  Widget toggle(String label) => MenuItemButton(
      style: standMenuItemStyle,
      closeOnActivate: false,
      leadingIcon: Icon(
          toggles[label] == true
              ? Icons.check_box_outlined
              : Icons.check_box_outline_blank,
          size: 18),
      onPressed: () => setState(() {
            toggles[label] = !(toggles[label] ?? false);
            event =
                'Демонстрация: $label — ${toggles[label]! ? "включено" : "выключено"}';
          }),
      child: Text(label));
  Widget radio(String group, String label, String initial) => MenuItemButton(
      style: standMenuItemStyle,
      leadingIcon: Icon(
          (selections[group] ?? initial) == label
              ? Icons.radio_button_checked
              : Icons.radio_button_unchecked,
          size: 18),
      onPressed: () => setState(() {
            selections[group] = label;
            event = 'Демонстрация: $group — $label';
          }),
      child: Text(label));
  Widget submenu(String title, List<Widget> children) => SubmenuButton(
      style: standMenuItemStyle, menuChildren: children, child: Text(title));

  Widget menu(String tooltip, List<Widget> children,
          Widget Function(VoidCallback open) button) =>
      MenuAnchor(
          onOpen: menuOpened,
          onClose: menuClosed,
          style: rdgenCompactMenuStyle.copyWith(
              backgroundColor: WidgetStatePropertyAll(
                  dark ? const Color(0xff262a30) : const Color(0xfff5f6f8))),
          menuChildren: children,
          builder: (_, controller, __) => Tooltip(
              message: tooltip,
              child: button(() {
                if (controller.isOpen) {
                  controller.close();
                } else {
                  controller.open();
                }
              })));

  Widget menuIcon(String glyph, VoidCallback open, {Color? color}) => SizedBox(
      width: 30,
      height: 30,
      child: TextButton(
          onPressed: open,
          style: rdgenToolbarButtonStyle(foreground: ink)
              .copyWith(padding: const WidgetStatePropertyAll(EdgeInsets.zero)),
          child: RdgenToolbarGlyph(glyph, color: color ?? ink)));

  List<Widget> displayMenu() => [
        item('Подогнать окно'),
        const Divider(height: 9, thickness: 1),
        for (final label in [
          'Исходный размер',
          'По размеру окна',
          'Свой масштаб'
        ])
          radio('Масштаб', label, 'По размеру окна'),
        submenu('Прокрутка', [
          for (final label in [
            'Автоматическая',
            'Полосы прокрутки',
            'По краям'
          ])
            radio('Прокрутка', label, 'Автоматическая')
        ]),
        const Divider(height: 9, thickness: 1),
        submenu('Качество изображения', [
          for (final label in [
            'Наилучшее качество',
            'Сбалансированное',
            'Быстрый отклик',
            'Настроить…'
          ])
            radio('Качество', label, 'Сбалансированное')
        ]),
        submenu('Кодек', [
          for (final label in [
            'Автоматически',
            'VP8',
            'VP9',
            'H.264',
            'H.265',
            'AV1'
          ])
            radio('Кодек', label, 'Автоматически')
        ]),
        submenu('Разрешение', [
          for (final label in [
            'Исходное',
            '1920 × 1080',
            '2560 × 1440',
            'Своё разрешение…'
          ])
            radio('Разрешение', label, 'Исходное')
        ]),
        const Divider(height: 9, thickness: 1),
        toggle('Показывать удалённый курсор'),
        toggle('Показывать монитор качества'),
        toggle('Отключить звук'),
        toggle('Режим приватности'),
      ];
  List<Widget> keyboardMenu() => [
        submenu('Режим клавиатуры', [
          for (final label in [
            'Устаревший режим',
            'Сопоставление клавиш',
            'Преобразование'
          ])
            radio('Клавиатура', label, 'Сопоставление клавиш')
        ]),
        submenu('Тип локальной клавиатуры', [
          for (final label in ['Автоматически', 'ANSI', 'ISO', 'JIS'])
            radio('Тип клавиатуры', label, 'Автоматически')
        ]),
        submenu('Источник ввода', [
          for (final label in ['Flutter', 'Системный'])
            radio('Источник ввода', label, 'Flutter')
        ]),
        const Divider(height: 9, thickness: 1),
        toggle('Только просмотр'),
        toggle('Показывать мой курсор'),
        toggle('Отключить буфер обмена'),
        toggle('Копирование и вставка файлов'),
        const Divider(height: 9, thickness: 1),
        toggle('Относительный режим мыши'),
        toggle('Обратная прокрутка'),
        item('Скорость трекпада…'),
      ];
  List<Widget> controlMenu() => [
        item('Запросить повышение прав'),
        item('Пароль ОС…'),
        item('Отправить содержимое буфера как нажатия'),
        const Divider(height: 9, thickness: 1),
        item('Передача файлов'),
        item('Камера'),
        item('Терминал (бета)'),
        item('TCP-туннель'),
        item('Заметка…'),
        const Divider(height: 9, thickness: 1),
        item('Ctrl + Alt + Del'),
        item('Заблокировать компьютер'),
        item('Перезагрузить устройство'),
        toggle('Блокировать после завершения сеанса'),
        item('Поменяться сторонами'),
        item('Обновить изображение'),
      ];
  List<Widget> organizationMenu() => [
        if (organization == null)
          item('Организация не назначена', enabled: false),
        for (final name in bindings)
          MenuItemButton(
              style: standMenuItemStyle,
              leadingIcon: SizedBox(
                  width: 18,
                  child: organization == name
                      ? const Icon(Icons.check, size: 17)
                      : null),
              onPressed: () => activateOrganization(name),
              child: ConstrainedBox(
                  constraints: const BoxConstraints(maxWidth: 380),
                  child: Text(name,
                      maxLines: 1, overflow: TextOverflow.ellipsis))),
        const Divider(height: 9, thickness: 1),
        item('Назначить организацию…', onPressed: choose),
        item(
            deviceAlias == null
                ? 'Назначить псевдоним устройства'
                : 'Изменить псевдоним устройства',
            onPressed: assignAlias),
      ];

  Widget toolbar() {
    final buttons = <Widget>[
      action(
          pinned ? Icons.push_pin : Icons.push_pin_outlined, 'Закрепить панель',
          () {
        setState(() {
          pinned = !pinned;
          collapsed = false;
        });
        scheduleHide();
      }, color: pinned ? const Color(0xffef7f1a) : null),
      if (total > 1)
        menu(
            'Выбрать монитор',
            [
              for (int i = 0; i < total; i++)
                MenuItemButton(
                    style: standMenuItemStyle,
                    leadingIcon: Icon(
                        current == i
                            ? Icons.radio_button_checked
                            : Icons.radio_button_unchecked,
                        size: 18),
                    onPressed: () => setState(() => current = i),
                    child: Text('Монитор ${i + 1}')),
              const Divider(height: 9, thickness: 1),
              toggle('Показывать дисплеи в отдельных окнах'),
            ],
            (open) => SizedBox(
                height: 30,
                child: TextButton(
                    onPressed: open,
                    style: rdgenToolbarButtonStyle(
                            background: dark
                                ? const Color(0xff21464b)
                                : const Color(0xffdcebee),
                            border: const Color(0xff356068))
                        .copyWith(
                            padding:
                                const WidgetStatePropertyAll(EdgeInsets.zero)),
                    child:
                        RdgenDisplayCounter(current: current, total: total)))),
      action(Icons.mouse_outlined, 'Полноэкранный режим',
          () => log('Демонстрация: переключение полноэкранного режима')),
      menu('Параметры изображения', displayMenu(),
          (open) => menuIcon('settings', open)),
      menu('Клавиатура и мышь', keyboardMenu(),
          (open) => menuIcon('keyboard', open)),
      menu('Действия', controlMenu(), (open) => menuIcon('bolt', open)),
      separator(),
      if (bindings.isEmpty)
        Tooltip(
            message: 'Организация сеанса',
            child:
                RdgenOrganizationToolbarButton(name: null, onPressed: choose))
      else
        menu(
            'Организация сеанса',
            organizationMenu(),
            (open) => RdgenOrganizationToolbarButton(
                name: organization, onPressed: open)),
      menu(
          'Ещё',
          [
            Row(mainAxisSize: MainAxisSize.min, children: [
              menu('Чат', [item('Текстовый чат'), item('Голосовой вызов')],
                  (open) => menuIcon('chat', open)),
              Tooltip(
                  message: recording ? 'Остановить запись' : 'Запись сеанса',
                  child: menuIcon(
                      'record',
                      () => setState(() {
                            recording = !recording;
                            event = recording
                                ? 'Демонстрация: запись включена'
                                : 'Демонстрация: запись выключена';
                          }),
                      color: recording ? Colors.redAccent : null)),
            ]),
          ],
          (open) => menuIcon('more', open)),
      action(Icons.close, 'Завершить тестовый сеанс',
          () => log('Демонстрация: сеанс завершён. Реальных соединений нет.')),
    ];
    return SingleChildScrollView(
        scrollDirection: Axis.horizontal,
        child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 5),
            child: Row(mainAxisSize: MainAxisSize.min, children: [
              for (int i = 0; i < buttons.length; i++) ...[
                if (i > 0) const SizedBox(width: 5),
                buttons[i],
              ],
            ])));
  }

  Widget desktop() => MouseRegion(
      onHover: (_) => scheduleHide(),
      child: Stack(children: [
        Positioned.fill(
            child: GestureDetector(
                onTap: () => log('Нажатие на рабочий стол прошло мимо панели'),
                child: Container(
                    decoration: BoxDecoration(
                        gradient: LinearGradient(
                            begin: Alignment.topLeft,
                            end: Alignment.bottomRight,
                            colors: dark
                                ? const [Color(0xff182432), Color(0xff334c66)]
                                : const [
                                    Color(0xffdce8f1),
                                    Color(0xffb6cedf)
                                  ])),
                    child: Center(
                        child:
                            Column(mainAxisSize: MainAxisSize.min, children: [
                      Icon(Icons.desktop_windows_outlined,
                          size: 64,
                          color: dark ? Colors.white24 : Colors.black26),
                      const SizedBox(height: 12),
                      Text('Тестовый рабочий стол',
                          style: TextStyle(
                              fontSize: 24,
                              color: dark ? Colors.white54 : Colors.black54)),
                      const SizedBox(height: 8),
                      Text('Устройство: ${deviceAlias ?? "DESKTOP-DEMO"}',
                          style: TextStyle(
                              color: dark ? Colors.white54 : Colors.black54)),
                      const SizedBox(height: 8),
                      Text(
                          'Монитор ${current + 1} из $total · ${organization ?? "Организация не выбрана"}',
                          style: TextStyle(
                              color: dark ? Colors.white54 : Colors.black54)),
                    ]))))),
        Positioned.fill(
            child: Theme(
                data: (dark ? ThemeData.dark() : ThemeData.light()).copyWith(
                    colorScheme: (dark
                            ? const ColorScheme.dark()
                            : const ColorScheme.light())
                        .copyWith(primary: const Color(0xffef7f1a))),
                child: StandIconStyle(
                    svg: svgIcons,
                    child: RdgenCompactSessionToolbar(
                        collapsed: collapsed,
                        assigned: organization != null,
                        organization: organization,
                        onExpand: () {
                          setState(() => collapsed = false);
                          scheduleHide();
                        },
                        onChoose: choose,
                        child: Builder(builder: (_) => toolbar()))))),
        Positioned(
            left: 12,
            bottom: 12,
            child: Text('ДЕМОНСТРАЦИЯ • без сервера и удалённого управления',
                style: TextStyle(
                    fontSize: 11,
                    color: dark ? Colors.white38 : Colors.black45))),
      ]));

  Widget settings() => SizedBox(
      width: 260,
      child: ListView(padding: const EdgeInsets.all(16), children: [
        const Text('Состояния панели',
            style: TextStyle(fontSize: 18, fontWeight: FontWeight.w600)),
        const SizedBox(height: 12),
        const Text(
            'Оболочка взята из клиента. Меню и действия — демонстрационные.',
            style: TextStyle(color: Colors.black54)),
        SwitchListTile(
            contentPadding: EdgeInsets.zero,
            title: const Text('Свернуть'),
            value: collapsed,
            onChanged: (v) => setState(() {
                  collapsed = v;
                  if (v) pinned = false;
                })),
        SwitchListTile(
            contentPadding: EdgeInsets.zero,
            title: const Text('Закрепить'),
            value: pinned,
            onChanged: (v) {
              setState(() {
                pinned = v;
                if (v) collapsed = false;
              });
              scheduleHide();
            }),
        SwitchListTile(
            contentPadding: EdgeInsets.zero,
            title: const Text('Организация выбрана'),
            value: organization != null,
            onChanged: (v) => setState(() {
                  if (v && bindings.isEmpty) bindings.add(organizations.first);
                  organization = v ? bindings.first : null;
                })),
        SwitchListTile(
            contentPadding: EdgeInsets.zero,
            title: const Text('Устройство без организаций'),
            value: bindings.isEmpty,
            onChanged: (value) => setState(() {
                  if (value) {
                    bindings.clear();
                    organization = null;
                  } else {
                    bindings.addAll(organizations.take(2));
                  }
                })),
        SwitchListTile(
            contentPadding: EdgeInsets.zero,
            title: const Text('Псевдоним уже задан'),
            value: deviceAlias != null,
            onChanged: (value) => setState(
                () => deviceAlias = value ? 'Рабочее место оператора' : null)),
        OutlinedButton(
            onPressed: choose, child: const Text('Выбрать организацию')),
        const SizedBox(height: 16),
        SwitchListTile(
            contentPadding: EdgeInsets.zero,
            title: const Text('Новые SVG-иконки'),
            subtitle: const Text('Выключить для сравнения с клиентом'),
            value: svgIcons,
            onChanged: (value) => setState(() => svgIcons = value)),
        const Text('Количество мониторов'),
        DropdownButton<int>(
            isExpanded: true,
            value: total,
            items: [1, 2, 3, 4]
                .map((n) => DropdownMenuItem(value: n, child: Text('$n')))
                .toList(),
            onChanged: (v) => setState(() {
                  total = v!;
                  if (current >= total) current = 0;
                })),
        SwitchListTile(
            contentPadding: EdgeInsets.zero,
            title: const Text('Запись'),
            value: recording,
            onChanged: (v) => setState(() => recording = v)),
        SwitchListTile(
            contentPadding: EdgeInsets.zero,
            title: const Text('Тёмная тема сеанса'),
            value: dark,
            onChanged: (v) => setState(() => dark = v)),
        const Divider(height: 9, thickness: 1),
        const Text(
            'Язычок свёрнутой панели можно перетаскивать. Незакреплённая панель скрывается через 2 секунды после движения мыши. Для проверки узкой ширины уменьшите окно.'),
      ]));

  @override
  Widget build(BuildContext context) => Scaffold(
      appBar: AppBar(
          title: const Text('StatusDesk — стенд панели',
              style: TextStyle(fontSize: 17)),
          actions: [
            TextButton.icon(
                onPressed: () => setState(() => controls = !controls),
                icon: const Icon(Icons.tune, color: Colors.white),
                label: Text(
                    controls ? 'Скрыть настройки' : 'Показать настройки',
                    style: const TextStyle(color: Colors.white))),
          ]),
      body: Column(children: [
        Expanded(
            child: Row(children: [
          Expanded(child: ClipRect(child: desktop())),
          if (controls) settings()
        ])),
        Container(
            alignment: Alignment.centerLeft,
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
            color: const Color(0xfff1f2f4),
            child: Text(event,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: const TextStyle(fontSize: 12))),
      ]));
}
