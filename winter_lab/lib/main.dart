import 'dart:async';
import 'dart:ui' show PointMode;
import 'dart:math' as math;
import 'dart:typed_data';
import 'package:flutter/material.dart';
import 'package:flutter/scheduler.dart';

void main() => runApp(const WinterLab());

class WinterLab extends StatefulWidget {
  const WinterLab({super.key});
  @override
  State<WinterLab> createState() => _WinterLabState();
}

class _WinterLabState extends State<WinterLab> {
  bool dark = true;
  int mode = 0;
  int particles = 24;
  int activeFps = 60;
  bool useTimer = true;
  @override
  Widget build(BuildContext context) => MaterialApp(
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
          brightness: dark ? Brightness.dark : Brightness.light,
          colorSchemeSeed: const Color(0xffef7f1a),
          useMaterial3: false),
      home: Scaffold(
          body: Column(children: [
        SizedBox(
            height: 32,
            child: Row(children: [
              const SizedBox(width: 12),
              const Icon(Icons.home, size: 18),
              const SizedBox(width: 6),
              const Text('Главная'),
              const SizedBox(width: 24),
              const Icon(Icons.build, size: 16),
              const SizedBox(width: 6),
              const Text('Настройки'),
              const Spacer(),
              const Text('Новый зимний стенд'),
              const SizedBox(width: 16),
            ])),
        Expanded(
            child: Row(children: [
          SizedBox(
              width: 200,
              child: RepaintBoundary(
                  child: Stack(children: [
                Positioned.fill(
                    child: ColoredBox(
                        color: dark
                            ? const Color(0xff24252b)
                            : const Color(0xffeeeeF2))),
                const Positioned(
                    top: 12,
                    left: 36,
                    right: 36,
                    child: Image(
                        image: AssetImage('assets/logo.png'),
                        height: 60,
                        fit: BoxFit.contain)),
                const Positioned(
                    top: 96,
                    left: 20,
                    right: 16,
                    child: Text('Ваш рабочий стол',
                        style: TextStyle(fontSize: 19))),
                const Positioned(
                    top: 154,
                    left: 20,
                    right: 16,
                    child: Text(
                        'Ваш рабочий стол доступен с этим ID и паролем.',
                        style: TextStyle(fontSize: 12))),
                Positioned(
                    top: 202,
                    left: 20,
                    right: 12,
                    child: _board('ID', '506 778 791', Icons.copy, 22)),
                Positioned(
                    top: 274,
                    left: 20,
                    right: 12,
                    child: _board(
                        'Одноразовый пароль', 'z8f376', Icons.refresh, 14)),
                if (mode == 1 || mode == 3)
                  const Positioned(
                      bottom: 0,
                      left: 0,
                      right: 0,
                      child: RepaintBoundary(
                          child: SizedBox(
                              height: 32,
                              child: CustomPaint(painter: Ground())))),
                if (mode == 2 || mode == 3 || mode == 4)
                  Positioned.fill(
                      child: IgnorePointer(
                          child: SnowLayer(
                              count: particles,
                              activeFps: activeFps,
                              useTimer: useTimer,
                              drawSnow: mode != 4,
                              key: ValueKey(
                                  "$particles/$activeFps/$mode/$useTimer")))),
              ]))),
          Expanded(
              child: Padding(
                  padding: const EdgeInsets.all(24),
                  child: ListView(children: [
                    const Text('Зимняя тема — измерение нагрузки',
                        style: TextStyle(fontSize: 23)),
                    const SizedBox(height: 12),
                    const Text(
                        'Сравнивайте CPU и GPU с режимом «Пустой интерфейс». Измерять в release, после 20 секунд стабилизации.'),
                    const SizedBox(height: 20),
                    Wrap(
                        spacing: 8,
                        runSpacing: 8,
                        children: List.generate(
                            5,
                            (i) => ChoiceChip(
                                label: Text([
                                  'Пустой интерфейс',
                                  'Статичное оформление',
                                  'Только снег',
                                  'Всё вместе',
                                  'Кадры без рисования'
                                ][i]),
                                selected: mode == i,
                                onSelected: (_) => setState(() => mode = i)))),
                    const SizedBox(height: 16),
                    SwitchListTile(
                        title: const Text('Тёмная тема'),
                        value: dark,
                        onChanged: (v) => setState(() => dark = v)),
                    Wrap(
                        spacing: 8,
                        children: [16, 24, 32]
                            .map((n) => ChoiceChip(
                                label: Text('$n снежинки'),
                                selected: particles == n,
                                onSelected: (_) =>
                                    setState(() => particles = n)))
                            .toList()),
                    const SizedBox(height: 20),
                    Wrap(
                        spacing: 8,
                        children: [30, 60]
                            .map((n) => ChoiceChip(
                                label: Text('$n кадров/с'),
                                selected: activeFps == n,
                                onSelected: (_) =>
                                    setState(() => activeFps = n)))
                            .toList()),
                    Wrap(
                        spacing: 8,
                        children: [false, true]
                            .map((value) => ChoiceChip(
                                label: Text(value ? 'Таймер' : 'Ticker'),
                                selected: useTimer == value,
                                onSelected: (_) =>
                                    setState(() => useTimer = value)))
                            .toList()),
                    Text(
                        'Активно: $activeFps кадров/с • Без фокуса: 30 • Скрыто: 0'),
                    const Text(
                        'Кадры без рисования: тот же vsync и уведомления перерисовки, но без расчёта движения и без команд рисования.'),
                    const SizedBox(height: 12),
                    const Text(
                        'Физики, накоплений и взаимодействия нет. Статичное оформление пока — простой тестовый сугроб; ёлку и зимний логотип добавим отдельными PNG после замеров.'),
                    const SizedBox(height: 24),
                    const TextField(
                        decoration: InputDecoration(
                            labelText: 'Удалённый ID (заглушка)',
                            border: OutlineInputBorder())),
                    const SizedBox(height: 12),
                    Align(
                        alignment: Alignment.centerLeft,
                        child: ElevatedButton(
                            onPressed: () {},
                            child: const Text('Подключиться'))),
                  ]))),
        ])),
        const SizedBox(
            height: 24,
            child: Row(children: [
              SizedBox(width: 212),
              Icon(Icons.circle, color: Colors.teal, size: 8),
              SizedBox(width: 8),
              Text('Подключено (макет)')
            ])),
      ])));

  Widget _board(String label, String value, IconData icon, double size) =>
      Container(
          padding: const EdgeInsets.only(left: 8),
          decoration: const BoxDecoration(
              border:
                  Border(left: BorderSide(color: Color(0xffef7f1a), width: 2))),
          child:
              Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(label,
                style: const TextStyle(fontSize: 12, color: Colors.grey)),
            Row(children: [
              Expanded(child: Text(value, style: TextStyle(fontSize: size))),
              IconButton(onPressed: () {}, icon: Icon(icon, size: 18))
            ]),
          ]));
}

/// One fixed allocation for positions and speeds. Updates never rebuild widgets.
class SnowField extends ChangeNotifier {
  final Float32List x, y, speed;
  final Paint paint = Paint()
    ..color = const Color(0xbbeef4ff)
    ..strokeWidth = 1.6
    ..strokeCap = StrokeCap.round;
  final Float32List points;
  final math.Random random = math.Random(71239);
  SnowField(int count)
      : x = Float32List(count),
        y = Float32List(count),
        speed = Float32List(count),
        points = Float32List(count * 2) {
    for (var i = 0; i < count; i++) {
      x[i] = random.nextDouble();
      y[i] = random.nextDouble();
      speed[i] = 18 + random.nextDouble() * 16;
    }
  }
  void emptyFrame() => notifyListeners();

  void advance(double seconds, Size size) {
    if (size.isEmpty) return;
    for (var i = 0; i < x.length; i++) {
      y[i] += seconds * speed[i] / size.height;
      if (y[i] > 1) {
        y[i] -= 1;
        x[i] = random.nextDouble();
      }
    }
    notifyListeners();
  }
}

class SnowLayer extends StatefulWidget {
  final int count;
  final int activeFps;
  final bool drawSnow;
  final bool useTimer;
  const SnowLayer(
      {super.key,
      required this.count,
      this.activeFps = 60,
      this.useTimer = false,
      this.drawSnow = true});
  @override
  State<SnowLayer> createState() => _SnowLayerState();
}

class _SnowLayerState extends State<SnowLayer>
    with SingleTickerProviderStateMixin, WidgetsBindingObserver {
  late final SnowField field;
  late final Ticker ticker;
  Timer? timer;
  final clock = Stopwatch();
  Duration? last;
  Size size = Size.zero;
  int fps = 60;
  @override
  void initState() {
    super.initState();
    field = SnowField(widget.count);
    WidgetsBinding.instance.addObserver(this);
    ticker = createTicker(tick);
    didChangeAppLifecycleState(
        WidgetsBinding.instance.lifecycleState ?? AppLifecycleState.resumed);
  }

  void tick(Duration elapsed) {
    final previous = last;
    if (previous == null) {
      last = elapsed;
      return;
    }
    final delta = (elapsed - previous).inMicroseconds;
    if (delta + 500 < 1000000 ~/ fps) return;
    last = elapsed;
    step(delta);
  }

  void step(int delta) {
    if (widget.drawSnow) {
      field.advance(math.min(delta / 1000000, 0.1), size);
    } else {
      field.emptyFrame();
    }
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    fps = state == AppLifecycleState.resumed ? widget.activeFps : 30;
    final running = state == AppLifecycleState.resumed ||
        state == AppLifecycleState.inactive;
    last = null;
    timer?.cancel();
    timer = null;
    if (ticker.isActive) ticker.stop();
    clock.stop();
    clock.reset();
    if (!running) return;
    if (widget.useTimer) {
      clock.start();
      last = Duration.zero;
      timer =
          Timer.periodic(Duration(microseconds: (1000000 / fps).round()), (_) {
        final elapsed = clock.elapsed;
        final delta = (elapsed - last!).inMicroseconds;
        last = elapsed;
        step(delta);
      });
    } else {
      ticker.start();
    }
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    timer?.cancel();
    clock.stop();
    ticker.dispose();
    field.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => LayoutBuilder(builder: (context, c) {
        size = c.biggest;
        return RepaintBoundary(
            child: ClipRect(
                child: CustomPaint(
                    painter: SnowPainter(field, drawSnow: widget.drawSnow))));
      });
}

class SnowPainter extends CustomPainter {
  final SnowField field;
  final bool drawSnow;
  SnowPainter(this.field, {this.drawSnow = true}) : super(repaint: field);
  @override
  void paint(Canvas canvas, Size size) {
    if (!drawSnow) return;
    for (var i = 0; i < field.x.length; i++) {
      field.points[i * 2] = field.x[i] * size.width;
      field.points[i * 2 + 1] = field.y[i] * size.height;
    }
    canvas.drawRawPoints(PointMode.points, field.points, field.paint);
  }

  @override
  bool shouldRepaint(SnowPainter old) =>
      old.field != field || old.drawSnow != drawSnow;
}

class Ground extends CustomPainter {
  const Ground();
  @override
  void paint(Canvas c, Size s) {
    final p = Path()
      ..moveTo(0, s.height)
      ..lineTo(0, 12)
      ..quadraticBezierTo(s.width * .25, 0, s.width * .5, 14)
      ..quadraticBezierTo(s.width * .8, 25, s.width, 9)
      ..lineTo(s.width, s.height)
      ..close();
    c.drawPath(p, Paint()..color = const Color(0xffe5edf4));
  }

  @override
  bool shouldRepaint(Ground old) => false;
}
