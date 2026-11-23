import 'dart:typed_data';
import 'dart:ui' as ui;
import 'package:flutter_test/flutter_test.dart';
import 'package:statusdesk_winter_stand/snow_field.dart';

// Command recording only: GPU/raster and Windows CPU require the release stand.
void main() {
  test('Compare particle batches, cap details and independent layers', () {
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
    // ignore: avoid_print
    print('Median ms / 1000 recorded frames (not GPU or CPU %): $results');
    field.dispose();
  });
}
