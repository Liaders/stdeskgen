import 'dart:ui' as ui;
import 'package:flutter/gestures.dart';
import 'package:flutter/material.dart';
import 'package:flutter/scheduler.dart';
import 'package:flutter/services.dart';
import 'snow_field.dart';

const sidebarWidth = 260.0;
const orange = Color(0xffef7f1a);

class SnowPanel extends StatefulWidget {
  final bool dark, running;
  final SnowField field;
  const SnowPanel(
      {super.key,
      required this.dark,
      required this.running,
      required this.field});
  @override
  State<SnowPanel> createState() => _SnowPanelState();
}

class _SnowPanelState extends State<SnowPanel>
    with SingleTickerProviderStateMixin, WidgetsBindingObserver {
  late final Ticker _ticker;
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
  static const idRect = Rect.fromLTWH(20, 252, 220, 47);
  static const passwordRect = Rect.fromLTWH(20, 342, 220, 43);
  static const settingsRect = Rect.fromLTWH(203, 224, 36, 28);

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _ticker = createTicker((elapsed) {
      final delta = elapsed - _lastFrame;
      if (delta.inMicroseconds < 33000) return;
      _lastFrame = elapsed;
      widget.field.tick(delta.inMicroseconds / 1000000);
    });
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
    if (oldWidget.running != widget.running) _syncTicker();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    _foreground = state == AppLifecycleState.resumed;
    _syncTicker();
  }

  void _syncTicker() {
    final active = widget.running && _foreground;
    widget.field.enabled = active;
    if (active && !_ticker.isActive) {
      _lastFrame = Duration.zero;
      _ticker.start();
    }
    if (!active && _ticker.isActive) _ticker.stop();
  }

  ui.Picture _scene({bool mask = false}) {
    final recorder = ui.PictureRecorder();
    final canvas = Canvas(recorder);
    final logo = widget.dark ? _logo : _lightLogo;
    if (logo != null) {
      canvas.drawImageRect(
          logo,
          Rect.fromLTWH(0, 0, logo.width.toDouble(), logo.height.toDouble()),
          const Rect.fromLTWH(24, 27, 212, 101),
          Paint()..filterQuality = FilterQuality.medium);
    }
    final foreground =
        widget.dark ? const Color(0xfff4f4f6) : const Color(0xff262830);
    final muted =
        widget.dark ? const Color(0xffb0b3be) : const Color(0xff676c78);
    void text(String value, Offset position, double size, Color color,
        {FontWeight weight = FontWeight.w400}) {
      final painter = TextPainter(
          text: TextSpan(
              text: value,
              style: TextStyle(
                  fontFamily: 'Roboto',
                  fontSize: size,
                  height: 1.25,
                  fontWeight: weight,
                  color: mask ? Colors.white : color)),
          textDirection: TextDirection.ltr,
          textScaler: TextScaler.noScaling)
        ..layout(maxWidth: 220);
      painter.paint(canvas, position);
      painter.dispose();
    }

    text('Ваш рабочий стол', const Offset(20, 155), 20, foreground,
        weight: FontWeight.w500);
    text('Ваш рабочий стол доступен\nс этим ID и паролем.',
        const Offset(20, 192), 12, muted);
    text('ID', const Offset(24, 231), 12, muted);
    text('Одноразовый пароль', const Offset(24, 318), 12, muted);
    return recorder.endRecording();
  }

  Future<void> _prepare(Size size, {bool keepSnow = false}) async {
    if (size.height <= 0 || _logo == null) return;
    final revision = ++_revision;
    final picture = _scene();
    List<List<SnowLedge>>? columns;
    if (!keepSnow || !widget.field.ready) {
      final mask = _scene(mask: true);
      final raster = await mask.toImage(size.width.ceil(), 360);
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
          const bands = [
            (27, 76),
            (76, 130),
            (155, 184),
            (192, 207),
            (207, 225),
            (231, 248),
            (318, 336)
          ];
          for (var band = 0; band < bands.length; band++) {
            for (var y = bands[band].$1; y < bands[band].$2; y++) {
              final solid = (opaque(x, y) ? 1 : 0) +
                      (opaque(x - 1, y) ? 1 : 0) +
                      (opaque(x + 1, y) ? 1 : 0) >=
                  2;
              if (solid && opaque(x, y + 1)) {
                final limit = band < 2
                    ? 9.5
                    : band == 2
                        ? 3.2
                        : 0.8;
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
    }
    if (!mounted || revision != _revision) {
      picture.dispose();
      return;
    }
    final old = _picture;
    _picture = picture;
    if (columns != null) {
      widget.field
          .configure(size, columns, [idRect, passwordRect, settingsRect]);
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
                    ? const Color(0xff24262c)
                    : const Color(0xffeef0f4),
                child: Stack(children: [
                  Positioned.fill(
                      child: RepaintBoundary(
                          child:
                              CustomPaint(painter: _ScenePainter(_picture)))),
                  Positioned.fromRect(
                      rect: settingsRect,
                      child: IconButton(
                          padding: EdgeInsets.zero,
                          tooltip: 'Настройки — макет',
                          onPressed: () {},
                          icon: const Icon(Icons.build_outlined, size: 17))),
                  Positioned.fromRect(
                      rect: idRect,
                      child: _field(_id, 'ID', 23, Icons.copy_outlined)),
                  Positioned.fromRect(
                      rect: passwordRect,
                      child: _field(_password, 'Пароль', 17, Icons.refresh)),
                  Positioned.fill(
                      child: IgnorePointer(
                          child: RepaintBoundary(
                              child: CustomPaint(
                                  painter: SnowPainter(
                                      widget.field, widget.dark))))),
                ])));
      });

  Widget _field(TextEditingController controller, String label, double size,
          IconData icon) =>
      Container(
          decoration: const BoxDecoration(
              border: Border(left: BorderSide(color: orange, width: 2))),
          padding: const EdgeInsets.only(left: 9),
          child: TextField(
              controller: controller,
              style: TextStyle(fontSize: size),
              decoration: InputDecoration(
                  isDense: true,
                  border: InputBorder.none,
                  enabledBorder: InputBorder.none,
                  focusedBorder: InputBorder.none,
                  contentPadding: const EdgeInsets.symmetric(vertical: 9),
                  suffixIcon: IconButton(
                      tooltip: '$label — макет',
                      onPressed: () {},
                      icon: Icon(icon, size: 18)))));

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    _revision++;
    _ticker.dispose();
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
