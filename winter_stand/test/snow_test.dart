import 'dart:io';
import 'dart:ui' as ui;
import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:statusdesk_winter_stand/main.dart';
import 'package:statusdesk_winter_stand/snow_field.dart';
import 'package:statusdesk_winter_stand/snow_panel.dart';

void main() {
  test(
      'Floor never grows and particle pool stays bounded after extended snowfall and swipes',
      () {
    final field = SnowField();
    field.configure(const Size(260, 675),
        List.generate(130, (i) => [SnowLedge(i * 2, 90, 6, 0)]), []);
    final target = List<double>.of(field.floorTarget);
    for (var frame = 0; frame < 54000; frame++) {
      if (frame % 90 == 0) {
        field.sweep(const Offset(20, 665), const Offset(230, 662), 0.1);
      }
      if (frame % 91 == 0) {
        field.sweep(const Offset(20, 87), const Offset(230, 87), 0.1);
      }
      field.tick(1 / 30);
      expect(field.particles.length,
          lessThanOrEqualTo(SnowField.fallingCount + SnowField.maxDebris));
      if (frame % 300 == 0) {
        expect(field.floorTarget, target);
        for (var i = 0; i < target.length; i++) {
          expect(field.floor[i], lessThanOrEqualTo(target[i]));
        }
      }
    }
    for (var i = 0; i < 1500; i++) {
      field.tick(1 / 30);
    }
    expect(field.floor, target);
    field.dispose();
  });

  test('Sweeping protected inputs does not disturb snow', () {
    final field = SnowField();
    field.configure(const Size(260, 675), List.generate(130, (_) => []),
        [const Rect.fromLTWH(20, 250, 220, 50)]);
    final before = field.particles.map((p) => (p.x, p.y, p.vx, p.vy)).toList();
    field.sweep(const Offset(30, 260), const Offset(220, 270), 0.05);
    expect(field.particles.map((p) => (p.x, p.y, p.vx, p.vy)).toList(), before);
    field.dispose();
  });

  testWidgets(
      'Dark and light stand render, controls remain editable, preview export',
      (tester) async {
    tester.view.physicalSize = const Size(1280, 800);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    if (Platform.isWindows &&
        File('C:/Windows/Fonts/segoeui.ttf').existsSync()) {
      await tester.runAsync(() async {
        final loader = FontLoader('Roboto')
          ..addFont(Future.value(ByteData.sublistView(
              File('C:/Windows/Fonts/segoeui.ttf').readAsBytesSync())));
        await loader.load();
      });
    }
    final boundaryKey = GlobalKey();
    await tester.runAsync(() async {
      final icons = FontLoader('MaterialIcons')
        ..addFont(rootBundle.load('fonts/MaterialIcons-Regular.otf'));
      await icons.load();
    });
    await tester.pumpWidget(
        RepaintBoundary(key: boundaryKey, child: const WinterStand()));
    for (var i = 0; i < 5; i++) {
      await tester.runAsync(
          () => Future<void>.delayed(const Duration(milliseconds: 100)));
      await tester.pump(const Duration(milliseconds: 80));
    }
    expect(tester.takeException(), isNull);
    final panel = tester.widget<SnowPanel>(find.byType(SnowPanel));
    expect(panel.field.ready, true);
    final floorBefore = panel.field.floor.reduce((a, b) => a + b);
    final origin = tester.getTopLeft(find.byType(SnowPanel));
    final mouse = await tester.createGesture(kind: ui.PointerDeviceKind.mouse);
    await mouse.down(origin + Offset(20, panel.field.size.height - 8));
    await mouse.moveTo(origin + Offset(225, panel.field.size.height - 8));
    await mouse.up();
    expect(panel.field.floor.reduce((a, b) => a + b), lessThan(floorBefore));
    panel.field.reset();
    await tester.tap(find.text('Пауза снега'));
    await tester.pump(const Duration(milliseconds: 100));
    expect(find.text('Продолжить'), findsOneWidget);
    final id = find.byType(TextField).first;
    await tester.enterText(id, '123 456 789');
    await tester.pump(const Duration(seconds: 1));
    expect(find.text('123 456 789'), findsOneWidget);
    await tester.enterText(id, '506 778 791');
    FocusManager.instance.primaryFocus?.unfocus();
    await tester.pump(const Duration(milliseconds: 300));
    final folder = Platform.environment['RDGEN_WINTER_PREVIEW'];
    Future<void> snapshot(String name) async {
      if (folder == null) return;
      await tester.runAsync(() async {
        final boundary = boundaryKey.currentContext!.findRenderObject()!
            as RenderRepaintBoundary;
        final image = await boundary.toImage();
        final bytes = await image.toByteData(format: ui.ImageByteFormat.png);
        Directory(folder).createSync(recursive: true);
        await File('$folder/$name.png')
            .writeAsBytes(bytes!.buffer.asUint8List());
        image.dispose();
      });
    }

    await snapshot('winter-dark');
    await tester.tap(find.byType(Switch));
    for (var i = 0; i < 3; i++) {
      await tester.runAsync(
          () => Future<void>.delayed(const Duration(milliseconds: 50)));
      await tester.pump(const Duration(milliseconds: 100));
    }
    expect(find.text('Светлая тема'), findsOneWidget);
    expect(tester.takeException(), isNull);
    await snapshot('winter-light');
    await tester.pumpWidget(const SizedBox.shrink());
  });
}
