import 'dart:typed_data';
import 'dart:ui' as ui;
import 'package:flutter_test/flutter_test.dart';
import 'package:statusdesk_winter_stand/snow_field.dart';
import 'package:statusdesk_winter_stand/snowfall_sprites.dart';

// Command recording only: GPU/raster and Windows CPU require the release stand.
void main() {
  test('Compare particle batches, cap details and independent layers',
      () async {
    final field = SnowField();
    const size = ui.Size(260, 675);
    field.configure(
        size, List.generate(130, (i) => [SnowLedge(i * 2, 90, 6, 0.8)]), []);
    for (final group in field.capGroups) {
      for (final ledge in group) {
        ledge.depth = 0.8;
      }
    }
    final circles = SnowPainter(field, true, layer: SnowLayer.particles);
    final combined = SnowPainter(field, true);
    final actualBatches =
        SnowPainter(field, true, layer: SnowLayer.particles, batched: true);
    final buffers = List.generate(36, (_) => Float32List(132));
    final counts = List<int>.filled(36, 0);
    final paints = List.generate(
        36,
        (i) => ui.Paint()
          ..color = const ui.Color(0xfff2f6ff).withOpacity((i ~/ 3) / 12)
          ..strokeCap = ui.StrokeCap.round
          ..strokeWidth = 2 * (0.8 + (i % 3) * 0.6));
    void batches(ui.Canvas canvas) {
      counts.fillRange(0, counts.length, 0);
      for (final p in field.particles) {
        final alpha = ((0.55 + p.radius * 0.15) * 11).round().clamp(0, 11);
        final bucket = alpha * 3 + ((p.radius - 0.8) / 0.6).round().clamp(0, 2);
        final index = counts[bucket];
        buffers[bucket][index] = p.x;
        buffers[bucket][index + 1] = p.y;
        counts[bucket] += 2;
      }
      for (var i = 0; i < counts.length; i++) {
        if (counts[i] != 0) {
          canvas.drawRawPoints(ui.PointMode.points,
              Float32List.sublistView(buffers[i], 0, counts[i]), paints[i]);
        }
      }
    }

    final capPaint = ui.Paint()..color = const ui.Color(0xfff1f6fc);
    final shadow = ui.Paint()..color = const ui.Color(0x388fa4ba);
    final caps = field.capPaths;
    final reduced = <ui.Path>[];
    for (final group in field.capGroups) {
      final path = ui.Path()..moveTo(group.first.x - 1, group.first.y);
      for (var i = 0; i < group.length; i += 3) {
        path.lineTo(group[i].x, group[i].y - group[i].depth);
      }
      path
        ..lineTo(group.last.x + 1, group.last.y)
        ..close();
      reduced.add(path);
    }
    double measure(void Function(ui.Canvas) draw) {
      final samples = <int>[];
      for (var run = 0; run < 7; run++) {
        final watch = Stopwatch()..start();
        for (var frame = 0; frame < 1000; frame++) {
          final recorder = ui.PictureRecorder();
          draw(ui.Canvas(recorder));
          recorder.endRecording().dispose();
        }
        watch.stop();
        if (run > 0) samples.add(watch.elapsedMicroseconds);
      }
      samples.sort();
      return samples[samples.length ~/ 2] / 1000;
    }

    final results = <String, double>{
      '66 circles': measure((c) => circles.paint(c, size)),
      'production batched particles':
          measure((c) => actualBatches.paint(c, size)),
      'batched points (quantized radius)': measure(batches),
      'combined snow': measure((c) => combined.paint(c, size)),
      'independent layers, static settled snow':
          measure((c) => circles.paint(c, size)),
      'caps with shadows': measure((c) {
        for (final p in caps) {
          c.save();
          c.translate(0, 0.4);
          c.drawPath(p, shadow);
          c.restore();
          c.drawPath(p, capPaint);
        }
      }),
      'caps without small shadows': measure((c) {
        for (final p in caps) {
          c.drawPath(p, capPaint);
        }
      }),
      'reduced contour': measure((c) {
        for (final p in reduced) {
          c.drawPath(p, capPaint);
        }
      }),
    };
    final images = <ui.Image>[];
    for (var layer = 0; layer < 3; layer++) {
      final recorder = ui.PictureRecorder();
      final canvas = ui.Canvas(recorder);
      for (final flake in field.tileFlakes.where((p) => p.layer == layer)) {
        canvas.drawCircle(ui.Offset(flake.x * 260 + 12, flake.y * 675),
            flake.radius, capPaint);
      }
      final picture = recorder.endRecording();
      images.add(await picture.toImage(284, 675));
      picture.dispose();
    }
    field.lightweight = true;
    final imagePaint = ui.Paint()..filterQuality = ui.FilterQuality.low;
    void drawTiles(ui.Canvas c) {
      c.save();
      c.clipRect(ui.Offset.zero & size);
      for (var layer = 0; layer < 3; layer++) {
        final y =
            (field.textureTime * SnowField.tileSpeeds[layer]) % size.height;
        final x = field.tileSway(layer) - 12;
        final image = images[layer];
        final src = ui.Rect.fromLTWH(
            0, 0, image.width.toDouble(), image.height.toDouble());
        c.drawImageRect(image, src,
            ui.Rect.fromLTWH(x, y, size.width + 24, size.height), imagePaint);
        c.drawImageRect(
            image,
            src,
            ui.Rect.fromLTWH(x, y - size.height, size.width + 24, size.height),
            imagePaint);
      }
      c.restore();
    }

    results['cached image layers (rejected)'] = measure(drawTiles);
    final atlasRecorder = ui.PictureRecorder();
    ui.Canvas(atlasRecorder).drawCircle(const ui.Offset(6, 6), 4,
        ui.Paint()..color = const ui.Color(0xb3ffffff));
    final atlasPicture = atlasRecorder.endRecording();
    final atlas = await atlasPicture.toImage(12, 12);
    atlasPicture.dispose();
    final sprites = SnowSpritePainter(field, true, atlas);
    results['tiny atlas sprites'] = measure((c) => sprites.paint(c, size));
    Future<double> raster(void Function(ui.Canvas) draw) async {
      final samples = <int>[];
      for (var run = 0; run < 4; run++) {
        final watch = Stopwatch()..start();
        for (var frame = 0; frame < 30; frame++) {
          final recorder = ui.PictureRecorder();
          draw(ui.Canvas(recorder));
          final picture = recorder.endRecording();
          final image = await picture.toImage(260, 675);
          image.dispose();
          picture.dispose();
        }
        watch.stop();
        if (run > 0) samples.add(watch.elapsedMicroseconds);
      }
      samples.sort();
      return samples[1] / 1000;
    }

    field.lightweight = false;
    final circleRaster = await raster((c) => circles.paint(c, size));
    field.lightweight = true;
    final tileRaster = await raster(drawTiles);
    final spriteRaster = await raster((c) => sprites.paint(c, size));
    // ignore: avoid_print
    print(
        'Headless toImage median ms / 30 frames (not Windows CPU/GPU): circles=$circleRaster tiles=$tileRaster sprites=$spriteRaster');
    atlas.dispose();
    for (final image in images) {
      image.dispose();
    }
    // ignore: avoid_print
    print('Median ms / 1000 recorded frames (not GPU or CPU %): $results');
    field.dispose();
  });
}
