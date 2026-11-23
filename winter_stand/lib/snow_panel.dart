import 'dart:ui' as ui;
import 'dart:async';
import 'package:flutter/gestures.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'snow_field.dart';
import 'winter_tree.dart';
import 'client_layout.dart';

const sidebarWidth = ClientSidebarLayout.width;
const orange = Color(0xffef7f1a);

class SnowPanel extends StatefulWidget {
  final bool dark, running;
  final SnowField field;
  final int framesPerSecond;
  final bool batched;
  const SnowPanel(
      {super.key,
      required this.dark,
      required this.running,
      this.framesPerSecond = 30,
      this.batched = false,
      required this.field});
  @override
  State<SnowPanel> createState() => _SnowPanelState();
}

class _SnowPanelState extends State<SnowPanel> with WidgetsBindingObserver {
  Timer? _frameTimer;
  final _clock = Stopwatch();
  ui.Image? _logo, _lightLogo;
  ui.Picture? _picture;
  Size _size = Size.zero;
  Duration _lastFrame = Duration.zero;
  Offset? _previousPointer;
  bool _sweeping = false;
  Duration _previousTime = Duration.zero;
  bool _foreground = true;
  int _revision = 0;
  final _id = TextEditingController(text: '506 778 791');
  final _password = TextEditingController(text: 'z8f376');
  final _layout = ClientSidebarLayout();

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _syncTicker();
    _loadLogo();
  }

  Future<void> _loadLogo() async {
    final bytes = await rootBundle.load('assets/logo.png');
    final codec = await ui.instantiateImageCodec(bytes.buffer.asUint8List(),
        targetWidth: 440);
    final image = (await codec.getNextFrame()).image;
    codec.dispose();
    final data = await image.toByteData(format: ui.ImageByteFormat.rawRgba);
    if (data == null) {
      image.dispose();
      return;
    }
    final light = Uint8List.fromList(data.buffer.asUint8List());
    for (var i = 0; i < light.length; i += 4) {
      if (light[i] > 150 && light[i + 1] > 150 && light[i + 2] > 150) {
        light[i] = 35;
        light[i + 1] = 37;
        light[i + 2] = 43;
      }
    }
    ui.decodeImageFromPixels(
        light, image.width, image.height, ui.PixelFormat.rgba8888,
        (lightImage) {
      if (!mounted) {
        image.dispose();
        lightImage.dispose();
        return;
      }
      _logo = image;
      _lightLogo = lightImage;
      if (_size != Size.zero) _prepare(_size);
    });
  }

  @override
  void didUpdateWidget(SnowPanel oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.dark != widget.dark) _prepare(_size, keepSnow: true);
    if (oldWidget.running != widget.running ||
        oldWidget.framesPerSecond != widget.framesPerSecond) {
      _frameTimer?.cancel();
      _frameTimer = null;
      _syncTicker();
    }
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    _foreground = state == AppLifecycleState.resumed;
    _syncTicker();
  }

  void _syncTicker() {
    final active = widget.running && _foreground;
    widget.field.enabled = active;
    if (active && _frameTimer == null) {
      _lastFrame = Duration.zero;
      _clock
        ..reset()
        ..start();
      _frameTimer = Timer.periodic(
          Duration(microseconds: (1000000 / widget.framesPerSecond).round()),
          (_) {
        final elapsed = _clock.elapsed;
        final delta = elapsed - _lastFrame;
        _lastFrame = elapsed;
        widget.field.advance(delta.inMicroseconds / 1000000);
      });
    }
    if (!active) {
      _frameTimer?.cancel();
      _frameTimer = null;
      _clock.stop();
    }
  }

  ui.Picture _scene({bool mask = false}) {
    final recorder = ui.PictureRecorder();
    final canvas = Canvas(recorder);
    final logo = widget.dark ? _logo : _lightLogo;
    if (logo != null) {
      canvas.drawImageRect(
          logo,
          Rect.fromLTWH(0, 0, logo.width.toDouble(), logo.height.toDouble()),
          _layout.logo,
          Paint()..filterQuality = FilterQuality.medium);
    }
    final foreground =
        widget.dark ? const Color(0xfff4f4f6) : const Color(0xff262830);
    final muted =
        widget.dark ? const Color(0xffb0b3be) : const Color(0xff676c78);
    for (var i = 0; i < _layout.labels.length; i++) {
      final label = _layout.labels[i];
      final painter = TextPainter(
          text: TextSpan(
              text: label.$1,
              style: label.$3.copyWith(
                  color: mask
                      ? Colors.white
                      : i == 0
                          ? foreground
                          : muted)),
          textDirection: TextDirection.ltr)
        ..layout(maxWidth: sidebarWidth - 36);
      painter.paint(canvas, label.$2);
      painter.dispose();
    }
    if (!mask) {
      final border = Paint()..color = orange;
      canvas.drawRect(Rect.fromLTWH(20, _layout.idTop + 5, 2, 52), border);
      canvas.drawRect(Rect.fromLTWH(20, _layout.passwordTop, 2, 52), border);
      WinterTree(_size).paint(canvas, widget.dark);
    }
    return recorder.endRecording();
  }

  Future<void> _prepare(Size size, {bool keepSnow = false}) async {
    if (size.height <= 0 || _logo == null) return;
    final revision = ++_revision;
    final picture = _scene();
    List<List<SnowLedge>>? columns;
    if (!keepSnow || !widget.field.ready) {
      final mask = _scene(mask: true);
      final raster = await mask.toImage(
          size.width.ceil(), (_layout.passwordTop + 22).ceil());
      mask.dispose();
      final bytes = await raster.toByteData(format: ui.ImageByteFormat.rawRgba);
      if (bytes != null) {
        final rgba = bytes.buffer.asUint8List();
        // Logical-pixel mask is independent of monitor DPI and built only on layout changes.
        final width = raster.width;
        bool opaque(int x, int y) =>
            x >= 0 &&
            x < width &&
            y >= 0 &&
            y < raster.height &&
            rgba[(y * width + x) * 4 + 3] >= 110;
        columns = List.generate((size.width / SnowField.step).ceil(), (bin) {
          final x = (bin * SnowField.step).round();
          final ledges = <SnowLedge>[];
          final bands = _layout.bands;
          for (var band = 0; band < bands.length; band++) {
            for (var y = bands[band].$1; y < bands[band].$2; y++) {
              final solid = (opaque(x, y) ? 1 : 0) +
                      (opaque(x - 1, y) ? 1 : 0) +
                      (opaque(x + 1, y) ? 1 : 0) >=
                  2;
              if (solid && opaque(x, y + 1)) {
                final limit = band < 2
                    ? 4.0
                    : band < 4
                        ? 2.0
                        : 0.65;
                ledges.add(SnowLedge(
                    bin * SnowField.step, y.toDouble(), limit, 0,
                    band: band));
                break;
              }
            }
          }
          return ledges;
        });
      }
      raster.dispose();
      if (columns != null) WinterTree(size).addSurfaces(columns);
    }
    if (!mounted || revision != _revision) {
      picture.dispose();
      return;
    }
    final old = _picture;
    _picture = picture;
    if (columns != null) {
      widget.field.configure(size, columns, _layout.protectedAreas);
    }
    setState(() {});
    // The previous display list can still be referenced by the current frame.
    WidgetsBinding.instance.addPostFrameCallback((_) => old?.dispose());
  }

  void _move(PointerMoveEvent event) {
    if (!_sweeping ||
        event.kind != PointerDeviceKind.mouse ||
        event.buttons & kPrimaryMouseButton == 0 ||
        !widget.running) return;
    final point = event.localPosition;
    if (!widget.field.canSweep(point)) {
      _previousPointer = null;
      return;
    }
    final from = _previousPointer;
    if (from != null) {
      widget.field.sweep(from, point,
          (event.timeStamp - _previousTime).inMicroseconds / 1000000);
    }
    _previousPointer = point;
    _previousTime = event.timeStamp;
  }

  @override
  Widget build(BuildContext context) =>
      LayoutBuilder(builder: (context, constraints) {
        final next = Size(constraints.maxWidth, constraints.maxHeight);
        if (next != _size) {
          _size = next;
          WidgetsBinding.instance.addPostFrameCallback((_) {
            if (mounted) _prepare(next);
          });
        }
        return Listener(
            behavior: HitTestBehavior.opaque,
            onPointerDown: (event) {
              _sweeping = false;
              if (event.kind == PointerDeviceKind.mouse &&
                  event.buttons & kPrimaryMouseButton != 0 &&
                  widget.field.canSweep(event.localPosition)) {
                _sweeping = true;
                _previousPointer = event.localPosition;
                _previousTime = event.timeStamp;
              }
            },
            onPointerMove: _move,
            onPointerUp: (_) {
              _previousPointer = null;
              _sweeping = false;
            },
            onPointerCancel: (_) {
              _previousPointer = null;
              _sweeping = false;
            },
            child: ColoredBox(
                color: widget.dark
                    ? const Color(0xff24252b)
                    : const Color(0xfff1f0f4),
                child: Stack(children: [
                  Positioned.fill(
                      child: RepaintBoundary(
                          child:
                              CustomPaint(painter: _ScenePainter(_picture)))),
                  Positioned.fromRect(
                      rect: _layout.settings,
                      child: IconButton(
                          padding: EdgeInsets.zero,
                          tooltip: 'Настройки — макет',
                          onPressed: () {},
                          icon: const Icon(Icons.build_outlined, size: 17))),
                  Positioned.fromRect(
                      rect: _layout.id,
                      child: _field(_id, 'ID', 22, Icons.content_copy)),
                  Positioned.fromRect(
                      rect: _layout.password,
                      child: _field(_password, 'Пароль', 15, null)),
                  Positioned.fromRect(
                      rect: _layout.refresh,
                      child: IconButton(
                          padding: EdgeInsets.zero,
                          onPressed: () {},
                          icon: const Icon(Icons.refresh, size: 22))),
                  Positioned.fromRect(
                      rect: _layout.edit,
                      child: IconButton(
                          padding: EdgeInsets.zero,
                          onPressed: () {},
                          icon: const Icon(Icons.edit, size: 22))),
                  Positioned.fill(
                      child: IgnorePointer(
                          child: RepaintBoundary(
                              child: CustomPaint(
                                  painter: SnowPainter(
                                      widget.field, widget.dark,
                                      layer: SnowLayer.settled))))),
                  Positioned.fill(
                      child: IgnorePointer(
                          child: RepaintBoundary(
                              child: CustomPaint(
                                  painter: SnowPainter(
                                      widget.field, widget.dark,
                                      layer: SnowLayer.particles,
                                      batched: widget.batched))))),
                ])));
      });

  Widget _field(TextEditingController controller, String label, double size,
          IconData? icon) =>
      TextField(
          controller: controller,
          style: TextStyle(fontSize: size),
          decoration: InputDecoration(
              isDense: true,
              border: InputBorder.none,
              enabledBorder: InputBorder.none,
              focusedBorder: InputBorder.none,
              contentPadding: const EdgeInsets.symmetric(vertical: 6),
              suffixIconConstraints:
                  const BoxConstraints.tightFor(width: 28, height: 28),
              suffixIcon: icon == null
                  ? null
                  : IconButton(
                      padding: EdgeInsets.zero,
                      tooltip: '$label — макет',
                      onPressed: () {},
                      icon: Icon(icon, size: 18))));

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    _revision++;
    _frameTimer?.cancel();
    _clock.stop();
    _picture?.dispose();
    _logo?.dispose();
    _lightLogo?.dispose();
    _id.dispose();
    _password.dispose();
    super.dispose();
  }
}

class _ScenePainter extends CustomPainter {
  final ui.Picture? picture;
  const _ScenePainter(this.picture);
  @override
  void paint(Canvas canvas, Size size) {
    if (picture != null) canvas.drawPicture(picture!);
  }

  @override
  bool shouldRepaint(_ScenePainter oldDelegate) =>
      picture != oldDelegate.picture;
}
