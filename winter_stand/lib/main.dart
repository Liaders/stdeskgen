import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter/scheduler.dart';
import 'holiday_panel.dart';
import 'client_layout.dart';
import 'package:flutter_svg/flutter_svg.dart';

void main() => runApp(const WinterStand());

class WinterStand extends StatefulWidget {
  const WinterStand({super.key});
  @override
  State<WinterStand> createState() => _WinterStandState();
}

class _WinterStandState extends State<WinterStand> {
  bool dark = true, running = true;
  bool emptyWindow = false, showStatistics = true;
  final int framesPerSecond = 60;
  Color lightBackground = const Color(0xfff1f0f4);
  final field = SnowField();
  final stats = ValueNotifier<String>('Подготовка карты снега…');
  final List<int> _buildTimes = [], _rasterTimes = [];
  late final Timer _timer;
  int _lastFrames = 0;

  @override
  void initState() {
    super.initState();
    SchedulerBinding.instance.addTimingsCallback(_timings);
    _timer = Timer.periodic(const Duration(seconds: 1), (_) {
      if (!showStatistics || emptyWindow || !field.interactive) return;
      int percentile(List<int> times) {
        if (times.isEmpty) return 0;
        final sorted = List<int>.of(times)..sort();
        return sorted[((sorted.length - 1) * 0.95).round()];
      }

      final frames = field.particlePaints - _lastFrames;
      _lastFrames = field.particlePaints;
      const mode = 'Снег · 60 кадров/с';
      stats.value =
          '${running ? '$mode · Кадры снега: $frames/с · Лимит $framesPerSecond' : 'Пауза'}  ·  Кадр p95: UI ${(percentile(_buildTimes) / 1000).toStringAsFixed(1)} / raster ${(percentile(_rasterTimes) / 1000).toStringAsFixed(1)} мс';
      _buildTimes.clear();
      _rasterTimes.clear();
    });
  }

  void _timings(List<FrameTiming> frames) {
    if (!showStatistics || emptyWindow || !field.interactive) return;
    for (final f in frames) {
      if (_buildTimes.length < 120) {
        _buildTimes.add(f.buildDuration.inMicroseconds);
        _rasterTimes.add(f.rasterDuration.inMicroseconds);
      }
    }
  }

  @override
  Widget build(BuildContext context) => MaterialApp(
      debugShowCheckedModeBanner: false,
      title: 'StatusDesk — зимний стенд',
      theme: ThemeData(
          useMaterial3: false,
          brightness: dark ? Brightness.dark : Brightness.light,
          colorSchemeSeed: orange,
          scaffoldBackgroundColor:
              dark ? const Color(0xff191a1e) : const Color(0xfffafbfc),
          fontFamily: 'Roboto',
          visualDensity: VisualDensity.compact,
          inputDecorationTheme: const InputDecorationTheme(
              border: OutlineInputBorder(), isDense: true),
          elevatedButtonTheme: ElevatedButtonThemeData(
              style: ElevatedButton.styleFrom(
                  backgroundColor: orange,
                  foregroundColor: Colors.white,
                  elevation: 0,
                  shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(7))))),
      home: Scaffold(
          body: Column(children: [
        _header(),
        const Divider(height: 1),
        Expanded(
            child: emptyWindow
                ? const SizedBox.expand()
                : Row(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                        SizedBox(
                            width: sidebarWidth,
                            child: SnowPanel(
                                dark: dark,
                                running: running,
                                field: field,
                                framesPerSecond: framesPerSecond,
                                lightBackground: lightBackground,
                                onSettings: _showSettings)),
                        const VerticalDivider(width: 1),
                        Expanded(child: _workspace()),
                      ])),
      ])));

  Widget _header() => Builder(
      builder: (context) => SizedBox(
          height: 28,
          child: Row(children: [
            const SizedBox(width: 16),
            const Icon(Icons.home_outlined, size: 19, color: orange),
            const SizedBox(width: 8),
            const Text('Главная'),
            const SizedBox(width: 24),
            TextButton.icon(
                onPressed: () => _showSettings(context),
                icon: const Icon(Icons.build_outlined, size: 17),
                label: const Text('Настройки')),
            const SizedBox(width: 16),
            const Text('Кадры/с: ', style: TextStyle(fontSize: 12)),
            const Text('60'),
            const SizedBox(width: 12),
            TextButton(
                onPressed: () => setState(() => emptyWindow = !emptyWindow),
                child: Text(emptyWindow ? 'Вернуть стенд' : 'Пустое окно')),
            const Spacer(),
            Text('Зимний стенд',
                style: TextStyle(
                    fontSize: 12, color: Theme.of(context).hintColor)),
            const SizedBox(width: 18),
            Icon(dark ? Icons.dark_mode_outlined : Icons.light_mode_outlined,
                size: 18),
            Switch(
                value: dark,
                activeColor: orange,
                onChanged: (value) => setState(() => dark = value)),
            Text(dark ? 'Тёмная тема' : 'Светлая тема',
                style: const TextStyle(fontSize: 12)),
            const SizedBox(width: 16),
          ])));

  Future<void> _showSettings(BuildContext context) async {
    final controller = TextEditingController(
        text:
            '#${(lightBackground.value & 0xffffff).toRadixString(16).padLeft(6, '0').toUpperCase()}');
    try {
      await showDialog<void>(
          context: context,
          builder: (context) => StatefulBuilder(builder: (context, refresh) {
                final valid = RegExp(r'^#?[0-9a-fA-F]{6}$')
                    .hasMatch(controller.text.trim());
                void applyColor(Color color) {
                  setState(() => lightBackground = color);
                  controller.text =
                      '#${(color.value & 0xffffff).toRadixString(16).padLeft(6, '0').toUpperCase()}';
                  refresh(() {});
                }

                return AlertDialog(
                    title: const Text('Настройки снежного стенда'),
                    content: SizedBox(
                        width: 360,
                        child: Column(
                            mainAxisSize: MainAxisSize.min,
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              const Text('Фон левой панели в светлой теме'),
                              const SizedBox(height: 12),
                              Wrap(spacing: 8, children: [
                                for (final color in [
                                  const Color(0xfff1f0f4),
                                  const Color(0xffdce5ed),
                                  const Color(0xffc5d6df),
                                  const Color(0xffe8e0d5),
                                  const Color(0xffd8e3d7),
                                  const Color(0xffb9c9d4)
                                ])
                                  InkWell(
                                      onTap: () => applyColor(color),
                                      child: Container(
                                          width: 42,
                                          height: 36,
                                          decoration: BoxDecoration(
                                              color: color,
                                              borderRadius:
                                                  BorderRadius.circular(6),
                                              border: Border.all(
                                                  color:
                                                      color == lightBackground
                                                          ? orange
                                                          : Colors.grey))))
                              ]),
                              const SizedBox(height: 16),
                              TextField(
                                  controller: controller,
                                  decoration: InputDecoration(
                                      labelText: 'Цвет HEX',
                                      hintText: '#DCE5ED',
                                      errorText: valid
                                          ? null
                                          : 'Введите шесть цифр HEX'),
                                  onChanged: (value) {
                                    final clean =
                                        value.trim().replaceFirst('#', '');
                                    if (RegExp(r'^[0-9a-fA-F]{6}$')
                                        .hasMatch(clean)) {
                                      setState(() => lightBackground = Color(
                                          0xff000000 |
                                              int.parse(clean, radix: 16)));
                                    }
                                    refresh(() {});
                                  }),
                              const SizedBox(height: 10),
                              const Text(
                                  'Цвет применяется сразу. Для сравнения включите светлую тему.',
                                  style: TextStyle(fontSize: 12)),
                            ])),
                    actions: [
                      TextButton(
                          onPressed: () => Navigator.pop(context),
                          child: const Text('Готово'))
                    ]);
              }));
    } finally {
      controller.dispose();
    }
  }

  Widget _workspace() => Builder(builder: (context) {
        final muted = Theme.of(context).hintColor;
        final surface =
            dark ? const Color(0xff24262c) : const Color(0xfff0f2f6);
        return Padding(
            padding: const EdgeInsets.fromLTRB(12, 8, 12, 0),
            child: Column(children: [
              Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                  decoration: BoxDecoration(
                      border: Border.all(
                          color:
                              Theme.of(context).dividerColor.withOpacity(0.2)),
                      borderRadius: BorderRadius.circular(12)),
                  child: Row(children: [
                    const SizedBox(
                        width: 280,
                        child: TextField(
                            style: TextStyle(fontSize: 22),
                            decoration: InputDecoration(
                                hintText: '197 914 227',
                                contentPadding: EdgeInsets.symmetric(
                                    horizontal: 15, vertical: 6)))),
                    const SizedBox(width: 12),
                    ElevatedButton(
                        onPressed: () {},
                        child: const Text('Подключиться',
                            style: TextStyle(fontSize: 15))),
                    const Spacer(),
                    Container(
                        width: 1,
                        height: 24,
                        color: Theme.of(context).dividerColor),
                    const SizedBox(width: 12),
                    const Icon(Icons.person_outline, size: 18),
                    const SizedBox(width: 6),
                    const Text('Ай нур'),
                    const SizedBox(width: 12),
                    OutlinedButton(
                        onPressed: () {}, child: const Text('Войти в панель')),
                  ])),
              const SizedBox(height: 16),
              SingleChildScrollView(
                  scrollDirection: Axis.horizontal,
                  child: Row(children: [
                    for (final tab in [
                      'Последние сеансы',
                      'Избранное',
                      'Организации',
                      'Коллеги',
                      'Найдено',
                      'Доступные устройства',
                      'Адресная книга'
                    ])
                      Container(
                          padding: const EdgeInsets.fromLTRB(9, 10, 9, 12),
                          decoration: tab == 'Организации'
                              ? const BoxDecoration(
                                  border: Border(
                                      bottom:
                                          BorderSide(color: orange, width: 2)))
                              : null,
                          child: Text(tab,
                              style: TextStyle(
                                  fontSize: 12,
                                  color: tab == 'Организации' ? null : muted))),
                  ])),
              const Divider(height: 1),
              const SizedBox(height: 12),
              Expanded(
                  child: Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                    SizedBox(
                        width: 260,
                        child: Column(children: [
                          const TextField(
                              decoration: InputDecoration(
                                  prefixIcon: Icon(Icons.search, size: 19),
                                  hintText: 'Поиск')),
                          const SizedBox(height: 12),
                          for (final group in [
                            'Авангард-Сервис',
                            'Антикор',
                            'ГЭСК',
                            'ИП Федоров',
                            'Узорметалл',
                            'Устройства ООО «Статус»'
                          ])
                            SizedBox(
                                height: 28,
                                child: Row(children: [
                                  const Icon(
                                      IconData(0xe623,
                                          fontFamily: 'DeviceGroup'),
                                      size: 19,
                                      color: orange),
                                  const SizedBox(width: 8),
                                  Expanded(
                                      child: Text(group,
                                          style: const TextStyle(fontSize: 14),
                                          overflow: TextOverflow.ellipsis)),
                                ])),
                        ])),
                    const SizedBox(width: 14),
                    Expanded(
                        child: ListView(children: [
                      for (final device in [
                        ('Сервер', '151 401 475'),
                        ('Ай нур домашний', '506 778 791'),
                        ('Ай нур рабочий', '197 914 227'),
                        ('Касса', '723 541 192'),
                        ('Ноутбук', '347 829 116')
                      ])
                        Container(
                            height: 44,
                            margin: const EdgeInsets.only(bottom: 4),
                            decoration: BoxDecoration(
                                color: surface,
                                borderRadius: BorderRadius.circular(6)),
                            child: Row(children: [
                              Container(
                                  width: 42,
                                  height: 44,
                                  alignment: Alignment.center,
                                  decoration: BoxDecoration(
                                      color: clientPeerColor(device.$2),
                                      borderRadius:
                                          const BorderRadius.horizontal(
                                              left: Radius.circular(5))),
                                  child: SvgPicture.asset('assets/win.svg',
                                      width: 30, height: 30)),
                              const SizedBox(width: 8),
                              const Icon(Icons.circle,
                                  color: Color(0xff48b969), size: 6),
                              const SizedBox(width: 8),
                              Expanded(
                                  child: Column(
                                      mainAxisAlignment:
                                          MainAxisAlignment.center,
                                      crossAxisAlignment:
                                          CrossAxisAlignment.start,
                                      children: [
                                    Text(device.$1,
                                        style: const TextStyle(fontSize: 14)),
                                    Text(device.$2,
                                        style: TextStyle(
                                            fontSize: 11, color: muted))
                                  ])),
                              const Padding(
                                  padding: EdgeInsets.only(right: 8),
                                  child: Icon(Icons.more_vert, size: 18)),
                            ])),
                    ])),
                  ])),
              Align(
                  alignment: Alignment.centerLeft,
                  child: Padding(
                      padding: const EdgeInsets.symmetric(vertical: 10),
                      child: Text(
                          'Статичное новогоднее оформление. Только падающий снег, без физики и взаимодействия.',
                          style: TextStyle(fontSize: 12, color: muted)))),
              Wrap(
                  spacing: 12,
                  crossAxisAlignment: WrapCrossAlignment.center,
                  children: [
                    TextButton.icon(
                        onPressed: () => setState(() => running = !running),
                        icon: Icon(running ? Icons.pause : Icons.play_arrow,
                            size: 17),
                        label: Text(running ? 'Пауза снега' : 'Продолжить')),
                    TextButton.icon(
                        onPressed: field.reset,
                        icon: const Icon(Icons.refresh, size: 17),
                        label: const Text('Сбросить снег')),
                    TextButton(
                        onPressed: () => setState(() {
                              showStatistics = !showStatistics;
                              _buildTimes.clear();
                              _rasterTimes.clear();
                              _lastFrames = field.particlePaints;
                            }),
                        child: Text(showStatistics
                            ? 'Скрыть статистику'
                            : 'Показать статистику')),
                    const Text('Все подключения и действия клиента — заглушки.',
                        style: TextStyle(fontSize: 11)),
                  ]),
              if (showStatistics)
                Padding(
                    padding: const EdgeInsets.only(top: 6, bottom: 9),
                    child: ValueListenableBuilder<String>(
                        valueListenable: stats,
                        builder: (_, value, __) => Text(value,
                            style: TextStyle(fontSize: 10, color: muted)))),
            ]));
      });

  @override
  void dispose() {
    _timer.cancel();
    SchedulerBinding.instance.removeTimingsCallback(_timings);
    stats.dispose();
    field.dispose();
    super.dispose();
  }
}
