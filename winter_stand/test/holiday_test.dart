import 'dart:io';
import 'dart:ui' as ui;
import 'package:flutter/services.dart';
import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:statusdesk_winter_stand/main.dart';
import 'package:statusdesk_winter_stand/holiday_panel.dart';

void main() {
  test('Snow updates at 60 Hz while glow notifications are limited to 15 Hz',
      () {
    final field = SnowField();
    var snow = 0, glow = 0;
    field.addListener(() => snow++);
    field.glow.addListener(() => glow++);
    for (var i = 0; i < 60; i++) {
      field.advance(1 / 60);
    }
    expect(snow, 60);
    expect(glow, inInclusiveRange(14, 15));
    snow = 0;
    glow = 0;
    for (var i = 0; i < 30; i++) {
      field.advance(1 / 30);
    }
    expect(snow, 30);
    expect(glow, inInclusiveRange(14, 16));
    final flake = field.flakes.first;
    flake.x = -1;
    flake.y = 2;
    field.advance(0.1);
    expect(flake.x, inInclusiveRange(0, 1));
    expect(flake.y, lessThan(0));
    expect(flake.speed, inInclusiveRange(16, 38));
    field.dispose();
  });
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
    final model = tester.widget<SnowPanel>(find.byType(SnowPanel)).field;
    var updates = 0;
    void count() {
      updates++;
    }

    model.addListener(count);
    tester.binding.handleAppLifecycleStateChanged(AppLifecycleState.inactive);
    await tester.pump(const Duration(milliseconds: 200));
    expect(updates, inInclusiveRange(5, 6));
    updates = 0;
    tester.binding.handleAppLifecycleStateChanged(AppLifecycleState.resumed);
    await tester.pump(const Duration(milliseconds: 200));
    expect(updates, inInclusiveRange(11, 12));
    updates = 0;
    tester.binding.handleAppLifecycleStateChanged(AppLifecycleState.hidden);
    await tester.pump(const Duration(milliseconds: 200));
    expect(updates, 0);
    tester.binding.handleAppLifecycleStateChanged(AppLifecycleState.resumed);
    model.removeListener(count);
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
    await tester.tap(find.text('Показать статистику'));
    await tester.pump();
    await tester.tap(find.text('Скрыть статистику'));
    await tester.pump();
    await tester.tap(find.text('Настройки'));
    await tester.pump(const Duration(milliseconds: 250));
    await tester.tap(find.text('Снег и звезда').last);
    await tester.pump(const Duration(milliseconds: 250));
    await tester.tap(find.text('Пустые кадры — без эффектов').last);
    await tester.pump(const Duration(milliseconds: 250));
    expect(tester.widget<SnowPanel>(find.byType(SnowPanel)).effectMode,
        SnowEffectMode.empty);
    await tester.tap(find.text('Готово'));
    await tester.pump(const Duration(milliseconds: 300));
    final scene = tester.widget<SnowPanel>(find.byType(SnowPanel)).field;
    final frames = scene.particlePaints;
    await tester.pump(const Duration(milliseconds: 100));
    expect(scene.particlePaints, greaterThan(frames));
    await tester.pumpWidget(const SizedBox.shrink());
    expect(tester.takeException(), isNull);
  });
}
