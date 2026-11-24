import 'dart:math' as math;
import 'dart:async';
import 'dart:ui' as ui;
import 'package:flutter/material.dart';
import 'package:flutter/scheduler.dart';
import 'package:flutter/services.dart';
import 'client_layout.dart';
import 'holiday_tree.dart';

const sidebarWidth = ClientSidebarLayout.width;
const orange = Color(0xffef7f1a);

class SnowField extends ChangeNotifier {
  double time = 0;
  int particlePaints = 0;
  bool interactive = true;
  void reset() {
    time = 0;
    notifyListeners();
  }

  void advance(double dt) {
    time += dt;
    notifyListeners();
  }
}

class SnowPanel extends StatefulWidget {
  final bool dark, running;
  final SnowField field;
  final int framesPerSecond;
  final Color lightBackground;
  final ValueChanged<BuildContext>? onSettings;
  const SnowPanel(
      {super.key,
      required this.dark,
      required this.running,
      required this.field,
      this.framesPerSecond = 60,
      this.lightBackground = const Color(0xfff1f0f4),
      this.onSettings});
  @override
  State<SnowPanel> createState() => _SnowPanelState();
}

class _SnowPanelState extends State<SnowPanel>
    with SingleTickerProviderStateMixin, WidgetsBindingObserver {
  late final Ticker _ticker;
  Duration _last = Duration.zero;
  int _nextFrame = 0;
  bool _visible = true;
  final _layout = ClientSidebarLayout();
  ui.Image? _scene;
  Size _size = Size.zero;
  int _revision = 0;
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _ticker = createTicker((elapsed) {
      final delta = elapsed - _last;
      if (elapsed.inMicroseconds < _nextFrame) return;
      _nextFrame = (((elapsed.inMicroseconds / (1000000 / 60)).floor() + 1) *
              (1000000 / 60))
          .round();
      _last = elapsed;
      widget.field.advance(delta.inMicroseconds.clamp(0, 100000) / 1000000);
    });
    _sync();
  }

  void _sync() {
    if (widget.running && _visible && !_ticker.isActive) {
      _last = Duration.zero;
      _nextFrame = 0;
      _ticker.start();
    } else if ((!widget.running || !_visible) && _ticker.isActive) {
      _ticker.stop();
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
    final data = await rootBundle.load('assets/logo.png');
    final codec = await ui.instantiateImageCodec(data.buffer.asUint8List(),
        targetWidth: 440);
    var logo = (await codec.getNextFrame()).image;
    codec.dispose();
    if (!widget.dark) {
      final bytes = await logo.toByteData(format: ui.ImageByteFormat.rawRgba);
      if (bytes != null) {
        final pixels = bytes.buffer.asUint8List();
        for (var i = 0; i < pixels.length; i += 4) {
          if (pixels[i] > 150 && pixels[i + 1] > 150 && pixels[i + 2] > 150) {
            pixels[i] = 48;
            pixels[i + 1] = 50;
            pixels[i + 2] = 56;
          }
        }
        final ready = Completer<ui.Image>();
        ui.decodeImageFromPixels(pixels, logo.width, logo.height,
            ui.PixelFormat.rgba8888, ready.complete);
        final light = await ready.future;
        logo.dispose();
        logo = light;
      }
    }
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
    final bytes = await base.toByteData(format: ui.ImageByteFormat.rawRgba);
    final winter = ui.PictureRecorder();
    final c = Canvas(winter)..drawImage(base, Offset.zero, Paint());
    if (bytes != null) {
      final pixels = bytes.buffer.asUint8List();
      final snow = Paint()
        ..color = const Color(0xfff5f9ff)
        ..strokeWidth = 2.4
        ..strokeCap = StrokeCap.round;
      for (var x = 1; x < base.width - 1; x += 2) {
        for (final band in _layout.bands) {
          snow.strokeWidth = band.$1 < 74 ? 2.1 : 0.9;
          for (var y = math.max(1, band.$1);
              y < math.min(base.height - 1, band.$2);
              y++) {
            if (pixels[(y * base.width + x) * 4 + 3] > 150 &&
                pixels[((y - 1) * base.width + x) * 4 + 3] < 80) {
              c.drawLine(
                  Offset(x - 1.0, y - 0.8), Offset(x + 0.8, y - 0.8), snow);
              break;
            }
          }
        }
      }
    }
    _tree(c, size);
    final decorated = winter.endRecording();
    final image =
        await decorated.toImage(size.width.ceil(), size.height.ceil());
    decorated.dispose();
    base.dispose();
    if (!mounted || revision != _revision) {
      image.dispose();
      return;
    }
    final old = _scene;
    setState(() => _scene = image);
    WidgetsBinding.instance.addPostFrameCallback((_) => old?.dispose());
  }

  void _tree(Canvas c, Size size) => paintHolidayTree(c, size);

  @override
  Widget build(BuildContext context) =>
      LayoutBuilder(builder: (context, constraints) {
        final size = constraints.biggest;
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
                      child: CustomPaint(painter: _Scene(_scene)))),
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
              Positioned.fill(
                  child: IgnorePointer(
                      child: RepaintBoundary(
                          child: CustomPaint(
                              painter: _Falling(widget.field, widget.dark))))),
            ]));
      });
  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    _ticker.dispose();
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
  final SnowField field;
  final bool dark;
  _Falling(this.field, this.dark) : super(repaint: field);
  @override
  void paint(Canvas c, Size s) {
    field.particlePaints++;
    final p = Paint()
      ..color =
          (dark ? Colors.white : const Color(0xff829bac)).withOpacity(0.65);
    c.save();
    c.clipRect(Offset.zero & s);
    for (var i = 0; i < 48; i++) {
      final x = ((i * 73.37) % s.width) + math.sin(field.time * 0.3 + i) * 3;
      final y =
          (i * 137.91 + field.time * (17 + i % 4 * 5)) % (s.height + 8) - 4;
      c.drawCircle(Offset(x, y), 0.7 + (i % 4) * 0.25, p);
    }
    final glow = 0.94 + math.sin(field.time * 1.4) * 0.08;
    c.save();
    c.translate(s.width - 57, s.height - 206);
    c.scale(glow);
    c.drawCircle(Offset.zero, 18, _halo);
    c.drawCircle(
        Offset.zero,
        1.6,
        Paint()
          ..color = const Color(0xfffff1bb)
              .withOpacity(0.55 + math.sin(field.time * 1.4) * 0.12));
    c.restore();
    c.restore();
  }

  @override
  bool shouldRepaint(_Falling old) => old.dark != dark || old.field != field;
}
