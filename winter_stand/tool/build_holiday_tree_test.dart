import 'dart:io';
import 'dart:ui' as ui;
import 'package:flutter_test/flutter_test.dart';
import 'package:statusdesk_winter_stand/holiday_tree.dart';

void main() {
  test(
      'Bake the existing decorated tree, gifts and snow into a transparent PNG',
      () async {
    final recorder = ui.PictureRecorder();
    final canvas = ui.Canvas(recorder)..scale(2);
    paintHolidayTree(canvas, const ui.Size(200, 240));
    final picture = recorder.endRecording();
    final image = await picture.toImage(400, 480);
    final data = await image.toByteData(format: ui.ImageByteFormat.png);
    await File('assets/holiday-tree.png')
        .writeAsBytes(data!.buffer.asUint8List());
    image.dispose();
    picture.dispose();
  });
}
