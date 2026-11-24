import 'dart:io';
import 'dart:ui' as ui;
import 'package:flutter/services.dart';
import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:statusdesk_winter_stand/main.dart';
import 'package:statusdesk_winter_stand/holiday_panel.dart';

void main() {
  testWidgets(
      'Decorated static scene and falling-only animation in both themes',
      (tester) async {
    tester.view.physicalSize = const Size(1280, 800);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    final key = GlobalKey();
    await tester.runAsync(() async {
      final loader = FontLoader('Roboto')
        ..addFont(Future.value(ByteData.sublistView(File(
                'C:/src/flutter/bin/cache/artifacts/material_fonts/roboto-regular.ttf')
            .readAsBytesSync())));
      await loader.load();
      await (FontLoader('MaterialIcons')
            ..addFont(rootBundle.load('fonts/MaterialIcons-Regular.otf')))
          .load();
      await (FontLoader('DeviceGroup')
            ..addFont(rootBundle.load('assets/device_group.ttf')))
          .load();
    });
    await tester
        .pumpWidget(RepaintBoundary(key: key, child: const WinterStand()));
    for (var i = 0; i < 8; i++) {
      await tester.runAsync(
          () => Future<void>.delayed(const Duration(milliseconds: 80)));
      await tester.pump(const Duration(milliseconds: 50));
    }
    expect(tester.takeException(), isNull);
    expect(
        tester.widget<SnowPanel>(find.byType(SnowPanel)).framesPerSecond, 60);
    final output = Platform.environment['RDGEN_WINTER_PREVIEW'];
    if (output != null) {
      await tester.runAsync(() async {
        final boundary =
            key.currentContext!.findRenderObject()! as RenderRepaintBoundary;
        final image = await boundary.toImage();
        final bytes = await image.toByteData(format: ui.ImageByteFormat.png);
        Directory(output).createSync(recursive: true);
        await File('$output/holiday-v2.png')
            .writeAsBytes(bytes!.buffer.asUint8List());
        image.dispose();
      });
    }
    await tester.tap(find.byType(Switch));
    await tester.pump();
    await tester.runAsync(
        () => Future<void>.delayed(const Duration(milliseconds: 200)));
    await tester.pump();
    expect(tester.takeException(), isNull);
    await tester.pumpWidget(const SizedBox.shrink());
  });
}
