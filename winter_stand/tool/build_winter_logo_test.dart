import 'dart:async';
import 'dart:io';
import 'dart:math' as math;
import 'dart:ui' as ui;
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';

// Offline composition: preserve the original logo, paint only a separate snow overlay.
void main() {
  test('Bake snow above original letter contours without redrawing the logo',
      () async {
    final codec = await ui
        .instantiateImageCodec(File('assets/logo.png').readAsBytesSync());
    final original = (await codec.getNextFrame()).image;
    codec.dispose();
    final rgba =
        (await original.toByteData(format: ui.ImageByteFormat.rawRgba))!
            .buffer
            .asUint8List();
    final paths = <ui.Path>[];
    for (final band in [(18, 190), (280, 460)]) {
      final runs = <List<ui.Offset>>[];
      var points = <ui.Offset>[];
      for (var x = 12; x < original.width - 12; x += 2) {
        int? top;
        for (var y = band.$1; y < band.$2; y++) {
          if (rgba[(y * original.width + x) * 4 + 3] > 220 &&
              rgba[((y + 2) * original.width + x) * 4 + 3] > 220) {
            top = y;
            break;
          }
        }
        if (top == null ||
            points.isNotEmpty && (top - points.last.dy).abs() > 9) {
          if (points.length > 12) runs.add(points);
          points = [];
        }
        if (top != null) points.add(ui.Offset(x.toDouble(), top.toDouble()));
      }
      if (points.length > 12) runs.add(points);
      for (final run in runs) {
        final smooth = List.generate(run.length, (i) {
          final values = [
            for (var j = math.max(0, i - 3);
                j <= math.min(run.length - 1, i + 3);
                j++)
              run[j].dy
          ]..sort();
          return ui.Offset(run[i].dx, values[values.length ~/ 2]);
        });
        final path = ui.Path()..moveTo(smooth.first.dx, smooth.first.dy + 1);
        for (var i = 0; i < smooth.length; i++) {
          final edge = math.min(1.0, math.min(i, smooth.length - 1 - i) / 8);
          final depth =
              (7 + 2 * math.sin(i * 0.11) + 1.2 * math.sin(i * 0.31)) * edge;
          path.lineTo(smooth[i].dx, smooth[i].dy - depth);
        }
        for (final p in smooth.reversed) {
          path.lineTo(p.dx, p.dy + 1.5);
        }
        paths.add(path..close());
      }
    }
    for (final dark in [true, false]) {
      ui.Image base = original;
      if (!dark) {
        final pixels = Uint8List.fromList(rgba);
        for (var i = 0; i < pixels.length; i += 4) {
          if (pixels[i] > 150 && pixels[i + 1] > 150 && pixels[i + 2] > 150) {
            pixels[i] = 48;
            pixels[i + 1] = 50;
            pixels[i + 2] = 56;
          }
        }
        final ready = Completer<ui.Image>();
        ui.decodeImageFromPixels(pixels, original.width, original.height,
            ui.PixelFormat.rgba8888, ready.complete);
        base = await ready.future;
      }
      final recorder = ui.PictureRecorder();
      final canvas = ui.Canvas(recorder);
      canvas.drawImage(base, ui.Offset.zero, ui.Paint());
      for (final path in paths) {
        canvas.drawPath(
            path,
            ui.Paint()
              ..shader = ui.Gradient.linear(
                  path.getBounds().topCenter,
                  path.getBounds().bottomCenter,
                  [const ui.Color(0xffffffff), const ui.Color(0xffd8e6ee)]));
      }
      final picture = recorder.endRecording();
      final result = await picture.toImage(original.width, original.height);
      final png = await result.toByteData(format: ui.ImageByteFormat.png);
      await File('assets/logo-winter-${dark ? 'dark' : 'light'}.png')
          .writeAsBytes(png!.buffer.asUint8List());
      result.dispose();
      picture.dispose();
      if (!dark) base.dispose();
    }
    original.dispose();
  });
}
