import 'dart:math' as math;
import 'dart:async';
import 'dart:typed_data';
import 'dart:ui' as ui;
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'client_layout.dart';

const sidebarWidth = ClientSidebarLayout.width;
const orange = Color(0xffef7f1a);

enum SnowEffectMode { all, snow, star, empty }

class FallingFlake {
  double x, y, speed;
  FallingFlake(this.x, this.y, this.speed);
}

class SnowField extends ChangeNotifier {
  final _random = math.Random();
  final flakes = <FallingFlake>[];
  double viewportHeight = 768;
  SnowField() {
    reset();
  }
  void _spawn(FallingFlake flake, {bool initial = false}) {
    flake.x = _random.nextDouble();
    flake.y =
        initial ? _random.nextDouble() : -0.02 - _random.nextDouble() * 0.04;
    flake.speed = 16 + _random.nextDouble() * 22;
  }

  final glow = ChangeNotifier();
  double _glowElapsed = 0;
  @override
  void dispose() {
    glow.dispose();
    super.dispose();
  }

  double time = 0;
  int particlePaints = 0;
  bool interactive = true;
  void reset() {
    time = 0;
    _glowElapsed = 0;
    if (flakes.isEmpty) {
      flakes.addAll(List.generate(48, (_) => FallingFlake(0, 0, 0)));
    }
    for (final flake in flakes) {
      _spawn(flake, initial: true);
    }
    notifyListeners();
    glow.notifyListeners();
  }

  void advance(double dt) {
    time += dt;
    final travel = dt / viewportHeight;
    for (final flake in flakes) {
      flake.y += flake.speed * travel;
      if (flake.y > 1.02) _spawn(flake);
    }
    notifyListeners();
    _glowElapsed += dt;
    if (_glowElapsed >= 1 / 15) {
      _glowElapsed %= 1 / 15;
      glow.notifyListeners();
    }
  }
}

class SnowPanel extends StatefulWidget {
  final bool dark, running;
  final SnowField field;
  final int framesPerSecond;
  final SnowEffectMode effectMode;
  final Color lightBackground;
  final ValueChanged<BuildContext>? onSettings;
  const SnowPanel(
      {super.key,
      required this.dark,
      required this.running,
      required this.field,
      this.framesPerSecond = 60,
      this.effectMode = SnowEffectMode.all,
      this.lightBackground = const Color(0xfff1f0f4),
      this.onSettings});
  @override
  State<SnowPanel> createState() => _SnowPanelState();
}

class _SnowPanelState extends State<SnowPanel> with WidgetsBindingObserver {
  Timer? _timer;
  final _clock = Stopwatch();
  Duration _last = Duration.zero;
  bool _visible = true;
  int? _timerFps;
  final _layout = ClientSidebarLayout();
  ui.Image? _scene;
  Size _size = Size.zero;
  int _revision = 0;
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    final state = WidgetsBinding.instance.lifecycleState;
    _visible = state == null ||
        state == AppLifecycleState.resumed ||
        state == AppLifecycleState.inactive;
    widget.field.interactive = state != AppLifecycleState.inactive;
    _sync();
  }

  void _sync() {
    final fps = widget.field.interactive ? widget.framesPerSecond : 30;
    if (_timer != null && _timerFps != fps) {
      _timer!.cancel();
      _timer = null;
    }
    if (widget.running && _visible && _timer == null) {
      _last = Duration.zero;
      _clock
        ..reset()
        ..start();
      _timerFps = fps;
      _timer =
          Timer.periodic(Duration(microseconds: (1000000 / fps).round()), (_) {
        final elapsed = _clock.elapsed, delta = elapsed - _last;
        _last = elapsed;
        widget.field.advance(delta.inMicroseconds.clamp(0, 100000) / 1000000);
      });
    } else if (!widget.running || !_visible) {
      _timer?.cancel();
      _timer = null;
      _clock.stop();
    }
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    _visible = state == AppLifecycleState.resumed ||
        state == AppLifecycleState.inactive;
    widget.field.interactive = state == AppLifecycleState.resumed;
    _sync();
  }

  @override
  void didUpdateWidget(SnowPanel oldWidget) {
    super.didUpdateWidget(oldWidget);
    _sync();
    if (oldWidget.dark != widget.dark) {
      _size = Size.zero;
    }
  }

  Future<void> _prepare(Size size) async {
    final revision = ++_revision;
    final data = await rootBundle.load(widget.dark
        ? 'assets/logo-winter-dark.png'
        : 'assets/logo-winter-light.png');
    final codec = await ui.instantiateImageCodec(data.buffer.asUint8List(),
        targetWidth: 440);
    final logo = (await codec.getNextFrame()).image;
    codec.dispose();
    final recorder = ui.PictureRecorder();
    final canvas = Canvas(recorder);
    final paint = Paint()..filterQuality = FilterQuality.medium;
    canvas.drawImageRect(
        logo,
        Rect.fromLTWH(0, 0, logo.width.toDouble(), logo.height.toDouble()),
        _layout.logo,
        paint);
    for (final label in _layout.labels) {
      final text = TextPainter(
          textDirection: TextDirection.ltr,
          text: TextSpan(
              text: label.$1,
              style: label.$3.copyWith(
                  color: widget.dark
                      ? const Color(0xffeeeeef)
                      : const Color(0xff303239))))
        ..layout(maxWidth: sidebarWidth - 36);
      text.paint(canvas, label.$2);
      text.dispose();
    }
    final picture = recorder.endRecording();
    final base = await picture.toImage(size.width.ceil(), size.height.ceil());
    picture.dispose();
    logo.dispose();
    final winter = ui.PictureRecorder();
    final c = Canvas(winter)..drawImage(base, Offset.zero, Paint());
    final treeData = await rootBundle.load('assets/holiday-tree.png');
    final treeCodec =
        await ui.instantiateImageCodec(treeData.buffer.asUint8List());
    final tree = (await treeCodec.getNextFrame()).image;
    treeCodec.dispose();
    c.drawImageRect(
        tree,
        Rect.fromLTWH(0, 0, tree.width.toDouble(), tree.height.toDouble()),
        Rect.fromLTWH(0, size.height - 240, size.width, 240),
        Paint()..filterQuality = FilterQuality.low);
    final decorated = winter.endRecording();
    final image =
        await decorated.toImage(size.width.ceil(), size.height.ceil());
    decorated.dispose();
    tree.dispose();
    base.dispose();
    if (!mounted || revision != _revision) {
      image.dispose();
      return;
    }
    final old = _scene;
    setState(() => _scene = image);
    WidgetsBinding.instance.addPostFrameCallback((_) => old?.dispose());
  }

  @override
  Widget build(BuildContext context) =>
      LayoutBuilder(builder: (context, constraints) {
        final size = constraints.biggest;
        widget.field.viewportHeight = size.height + 8;
        if (size != _size) {
          _size = size;
          WidgetsBinding.instance.addPostFrameCallback((_) {
            if (mounted) _prepare(size);
          });
        }
        return ColoredBox(
            color:
                widget.dark ? const Color(0xff24252b) : widget.lightBackground,
            child: Stack(children: [
              Positioned.fill(
                  child: RepaintBoundary(
                      child: CustomPaint(
                          isComplex: true, painter: _Scene(_scene)))),
              Positioned.fromRect(
                  rect: _layout.settings,
                  child: IconButton(
                      tooltip: 'Настройки стенда',
                      onPressed: () => widget.onSettings?.call(context),
                      icon: const Icon(Icons.build_outlined, size: 17))),
              Positioned.fromRect(
                  rect: _layout.id,
                  child: const TextField(
                      controller: null,
                      decoration: InputDecoration(
                          hintText: '506 778 791',
                          border: InputBorder.none,
                          isDense: true),
                      style: TextStyle(fontSize: 22))),
              Positioned.fromRect(
                  rect: _layout.password,
                  child: const Text('z8f376', style: TextStyle(fontSize: 15))),
              if (widget.effectMode != SnowEffectMode.star)
                Positioned.fill(
                    child: IgnorePointer(
                        child: RepaintBoundary(
                            child: CustomPaint(
                                willChange: true,
                                painter: _Falling(widget.field, widget.dark,
                                    empty: widget.effectMode ==
                                        SnowEffectMode.empty))))),
              if (widget.effectMode == SnowEffectMode.all ||
                  widget.effectMode == SnowEffectMode.star)
                Positioned(
                    left: size.width - 75,
                    top: size.height - 224,
                    width: 36,
                    height: 36,
                    child: IgnorePointer(
                        child: RepaintBoundary(
                            child: CustomPaint(
                                willChange: true,
                                painter: _Glow(widget.field))))),
            ]));
      });
  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    _timer?.cancel();
    _clock.stop();
    _revision++;
    _scene?.dispose();
    super.dispose();
  }
}

class _Scene extends CustomPainter {
  final ui.Image? image;
  _Scene(this.image);
  @override
  void paint(Canvas c, Size s) {
    if (image != null) c.drawImage(image!, Offset.zero, Paint());
  }

  @override
  bool shouldRepaint(_Scene old) => old.image != image;
}

class _Falling extends CustomPainter {
  final SnowField field;
  final bool dark;
  final List<Float32List> _points = List.generate(4, (_) => Float32List(24));
  late final List<Paint> _paints = List.generate(
      4,
      (i) => Paint()
        ..color =
            (dark ? Colors.white : const Color(0xff829bac)).withOpacity(0.65)
        ..strokeWidth = 2 * (0.7 + i * 0.25)
        ..strokeCap = StrokeCap.round);
  final bool empty;
  _Falling(this.field, this.dark, {this.empty = false}) : super(repaint: field);
  @override
  void paint(Canvas c, Size s) {
    field.particlePaints++;
    if (empty) return;
    c.save();
    c.clipRect(Offset.zero & s);
    for (var group = 0; group < 4; group++) {
      final points = _points[group];
      for (var j = 0; j < 12; j++) {
        final i = j * 4 + group;
        final flake = field.flakes[i];
        points[j * 2] = flake.x * s.width;
        points[j * 2 + 1] = flake.y * (s.height + 8) - 4;
      }
      c.drawRawPoints(ui.PointMode.points, points, _paints[group]);
    }
    c.restore();
  }

  @override
  bool shouldRepaint(_Falling old) =>
      old.dark != dark || old.field != field || old.empty != empty;
}

class _Glow extends CustomPainter {
  final SnowField field;
  final Paint _halo = Paint()
    ..shader = ui.Gradient.radial(Offset.zero, 18, [
      const Color(0x66ffd773),
      const Color(0x22ffd773),
      const Color(0x00ffd773)
    ], [
      0,
      0.4,
      1
    ]);
  final Paint _core = Paint();
  _Glow(this.field) : super(repaint: field.glow);
  @override
  void paint(Canvas c, Size s) {
    final glow = 0.94 + math.sin(field.time * 1.4) * 0.08;
    c.save();
    c.translate(18, 18);
    c.scale(glow);
    c.drawCircle(Offset.zero, 18, _halo);
    c.drawCircle(
        Offset.zero,
        1.6,
        _core
          ..color = const Color(0xfffff1bb)
              .withOpacity(0.55 + math.sin(field.time * 1.4) * 0.12));
    c.restore();
  }

  @override
  bool shouldRepaint(_Glow old) => old.field != field;
}
