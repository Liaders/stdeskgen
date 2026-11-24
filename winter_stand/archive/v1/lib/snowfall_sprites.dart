import 'dart:ui' as ui;
import 'dart:typed_data';
import 'package:flutter/material.dart';
import 'snow_field.dart';

/// One tiny cached atlas; only the flakes' bounding boxes are blended each frame.
class SnowfallSprites extends StatefulWidget {
  final SnowField field;
  final bool dark;
  const SnowfallSprites({super.key, required this.field, required this.dark});
  @override
  State<SnowfallSprites> createState() => _SnowfallSpritesState();
}

class _SnowfallSpritesState extends State<SnowfallSprites> {
  ui.Image? _atlas;
  @override
  void initState() {
    super.initState();
    _prepare();
  }

  Future<void> _prepare() async {
    final recorder = ui.PictureRecorder();
    Canvas(recorder).drawCircle(
        const Offset(6, 6), 4, Paint()..color = Colors.white.withOpacity(0.7));
    final picture = recorder.endRecording();
    final image = await picture.toImage(12, 12);
    picture.dispose();
    if (!mounted) {
      image.dispose();
      return;
    }
    setState(() => _atlas = image);
  }

  @override
  Widget build(BuildContext context) => CustomPaint(
      painter: SnowSpritePainter(widget.field, widget.dark, _atlas));

  @override
  void dispose() {
    _atlas?.dispose();
    super.dispose();
  }
}

class SnowSpritePainter extends CustomPainter {
  final SnowField field;
  final ui.Image? atlas;
  final SnowPainter interactive;
  final Paint _paint;
  late final Float32List _transforms;
  late final Float32List _rects;

  SnowSpritePainter(this.field, bool dark, this.atlas)
      : interactive = SnowPainter(field, dark, layer: SnowLayer.particles),
        _paint = Paint()
          ..filterQuality = FilterQuality.low
          ..colorFilter = ColorFilter.mode(
              dark ? const Color(0xfff2f6ff) : const Color(0xffafc5da),
              BlendMode.srcIn),
        super(repaint: field) {
    _transforms = Float32List(field.tileFlakes.length * 4);
    _rects = Float32List(field.tileFlakes.length * 4);
    for (var i = 0; i < field.tileFlakes.length; i++) {
      _transforms[i * 4] = field.tileFlakes[i].radius / 4;
      _rects[i * 4 + 2] = 12;
      _rects[i * 4 + 3] = 12;
    }
  }

  @override
  void paint(Canvas canvas, Size size) {
    final image = atlas;
    if (!field.ready || image == null) return;
    canvas.save();
    canvas.clipRect(Offset.zero & size);
    final hole = field.tileHole;
    if (hole != null) {
      canvas.clipPath(
          Path()
            ..fillType = PathFillType.evenOdd
            ..addRect(Offset.zero & size)
            ..addOval(hole),
          doAntiAlias: false);
    }
    final sway = [
      for (var layer = 0; layer < 3; layer++) field.tileSway(layer)
    ];
    final drops = [
      for (final speed in SnowField.tileSpeeds) field.textureTime * speed
    ];
    for (var i = 0; i < field.tileFlakes.length; i++) {
      final flake = field.tileFlakes[i];
      if (field.interactive && field.caughtFlakes.contains(flake)) {
        _transforms[i * 4 + 2] = -10000;
        _transforms[i * 4 + 3] = -10000;
        continue;
      }
      final inset = 6 * _transforms[i * 4];
      _transforms[i * 4 + 2] = flake.x * size.width + sway[flake.layer] - inset;
      _transforms[i * 4 + 3] =
          (flake.y * size.height + drops[flake.layer]) % size.height - inset;
    }
    canvas.drawRawAtlas(
        image, _transforms, _rects, null, BlendMode.srcOver, null, _paint);
    canvas.restore();
    if (field.interactive && field.debrisCount > 0) {
      interactive.paint(canvas, size);
    } else {
      field.particlePaints++;
    }
  }

  @override
  bool shouldRepaint(SnowSpritePainter oldDelegate) =>
      atlas != oldDelegate.atlas ||
      field != oldDelegate.field ||
      interactive.dark != oldDelegate.interactive.dark;
}
