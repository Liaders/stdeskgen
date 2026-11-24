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
      'All hits accumulate, half continue, and background mode freezes deposits',
      () {
    final field = SnowField()..lightweight = true;
    field.configure(
        const Size(260, 1000),
        List.generate(
            130,
            (i) => [
                  SnowLedge(i * 2, 100, 100, 0, band: 0),
                  SnowLedge(i * 2, 500, 100, 0, band: 10),
                ]),
        []);
    final ledges = field.columns[65];
    field.tileFlakes.clear();
    for (final ledge in ledges) {
      final y = (ledge.y - ledge.depth - 1.5) / 1000;
      field.tileFlakes
          .addAll([SnowTileFlake(0.5, y, 1, 0), SnowTileFlake(0.5, y, 1, 0)]);
    }
    field.reset();
    double mass(int band) => field.capGroups
        .expand((group) => group)
        .where((ledge) => ledge.band == band)
        .fold(0, (sum, ledge) => sum + ledge.depth);
    final letters = mass(0), branches = mass(10);
    field.advance(0.1);
    expect(mass(0) - letters, closeTo(6.4, 0.001));
    expect(mass(10) - branches, closeTo(6.4, 0.001));
    expect(field.caughtFlakes.length, 2);
    field.interactive = false;
    final before = mass(0) + mass(10),
        physics = field.physicsSteps,
        time = field.textureTime;
    for (var i = 0; i < 100; i++) {
      field.advance(0.1);
    }
    expect(mass(0) + mass(10), before);
    expect(field.physicsSteps, physics);
    expect(field.textureTime, greaterThan(time));
    field.dispose();
  });

  test('Loose snow deforms locally and leaves the permanent base at open edges',
      () {
    for (final direction in [-1, 1]) {
      final field = SnowField();
      field.configure(const Size(260, 675), List.generate(130, (_) => []), []);
      final debris = field.debrisCount;
      final start = direction > 0 ? 1.0 : 259.0;
      field.sweep(
          Offset(start, 667), Offset(start + direction * 1200, 667), 0.15);
      expect(field.floorVisible, false);
      expect(field.debrisCount, debris);
      for (var i = 0; i < 1800; i++) {
        field.tick(1 / 30);
      }
      expect(field.floorVisible, false);
      expect(field.floorHeightAt(130), field.baseHeightAt(130));
      expect(field.floor.first, 0);
      expect(field.floor.last, 0);
      expect(field.floor.every((h) => h < SnowField.floorMaxHeight), true);
      field.reset();
      expect(field.floorVisible, true);
      final before = List<double>.of(field.floor);
      field.sweep(const Offset(190, 667), const Offset(210, 667), 0.1);
      expect(field.floor, isNot(equals(before)));
      expect(field.floor[10], closeTo(before[10], 0.1));
      field.floor[60] = 200;
      field.previousFloor[60] = 200;
      field.sweep(const Offset(120, 575), const Offset(125, 575), 0.1);
      expect(field.floor.reduce((a, b) => a > b ? a : b),
          greaterThan(SnowField.floorMaxHeight));
      field.dispose();
    }
  });

  test('Cached snowfall reaches the middle without running individual physics',
      () {
    final field = SnowField()..lightweight = true;
    field.configure(const Size(260, 675), List.generate(130, (_) => []), []);
    for (var i = 0; i < 300; i++) {
      field.advance(1 / 30);
    }
    expect(field.physicsSteps, 0);
    expect(field.textureTime, closeTo(10, 0.001));
    expect(
        field.tileFlakes.where((p) {
          final y = field.tilePosition(p).dy;
          return y > 250 && y < 500;
        }).length,
        greaterThan(10));
    field.dispose();
  });

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
          expect(field.floor[i], lessThanOrEqualTo(SnowField.floorMaxHeight));
        }
      }
    }
    for (var i = 0; i < 1500; i++) {
      field.tick(1 / 30);
    }
    expect(field.floor.every((h) => h >= 0 && h <= SnowField.floorMaxHeight),
        true);
    field.dispose();
  });

  test('Protected inputs reject sweeping but do not hide snow', () async {
    final field = SnowField();
    field.configure(const Size(260, 675), List.generate(130, (_) => []),
        [const Rect.fromLTWH(20, 250, 220, 50)]);
    final before = field.particles.map((p) => (p.x, p.y, p.vx, p.vy)).toList();
    field.sweep(const Offset(30, 260), const Offset(220, 270), 0.05);
    expect(field.particles.map((p) => (p.x, p.y, p.vx, p.vy)).toList(), before);
    for (final p in field.particles) {
      p.x = -100;
      p.previousX = -100;
    }
    final p = field.particles.first;
    p.x = 30;
    p.y = 260;
    p.previousX = 30;
    p.previousY = 260;
    p.radius = 3;
    final recorder = ui.PictureRecorder();
    SnowPainter(field, true).paint(Canvas(recorder), field.size);
    final picture = recorder.endRecording();
    final image = await picture.toImage(260, 675);
    final rgba = await image.toByteData(format: ui.ImageByteFormat.rawRgba);
    expect(rgba!.getUint8((260 * 260 + 30) * 4 + 3), greaterThan(0));
    image.dispose();
    picture.dispose();
    field.dispose();
  });

  test(
      'Deposits spread into flat caps and airborne flakes receive varied impulses',
      () {
    final field = SnowField();
    field.configure(const Size(200, 650),
        List.generate(100, (i) => [SnowLedge(i * 2, 90, 4, 0)]), []);
    for (var drop = 0; drop < 200; drop++) {
      final ledge = field.columns[50].first;
      final p = field.particles.first;
      p.x = 100;
      p.y = ledge.y - ledge.depth - 1.1;
      p.radius = 1;
      p.vy = 60;
      p.vx = 0;
      field.tick(1 / 30);
    }
    for (var i = 1; i < 100; i++) {
      expect(
          (field.columns[i].first.depth - field.columns[i - 1].first.depth)
              .abs(),
          lessThan(1.0));
      expect(field.columns[i].first.depth, lessThanOrEqualTo(4.0));
    }
    for (var i = 0; i < field.particles.length; i++) {
      final p = field.particles[i];
      p.x = 100;
      p.y = 400;
      p.vx = 0;
      p.vy = 20;
    }
    field.sweep(const Offset(80, 400), const Offset(120, 410), 0.05);
    expect(field.particles.map((p) => p.vx.toStringAsFixed(1)).toSet().length,
        greaterThan(20));
    expect(field.particles.map((p) => p.vy.toStringAsFixed(1)).toSet().length,
        greaterThan(20));
    final steps = field.physicsSteps;
    for (var i = 0; i < 120; i++) {
      field.advance(1 / 120);
    }
    expect(field.physicsSteps - steps, inInclusiveRange(29, 30));
    expect(field.renderedFrames, 120);
    field.dispose();
  });

  testWidgets(
      'Dark and light stand render, controls remain editable, preview export',
      (tester) async {
    tester.view.physicalSize = const Size(1280, 800);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    if (File(
            'C:/src/flutter/bin/cache/artifacts/material_fonts/roboto-regular.ttf')
        .existsSync()) {
      await tester.runAsync(() async {
        final loader = FontLoader('Roboto')
          ..addFont(Future.value(ByteData.sublistView(File(
                  'C:/src/flutter/bin/cache/artifacts/material_fonts/roboto-regular.ttf')
              .readAsBytesSync())));
        await loader.load();
      });
    }
    final boundaryKey = GlobalKey();
    await tester.runAsync(() async {
      final icons = FontLoader('MaterialIcons')
        ..addFont(rootBundle.load('fonts/MaterialIcons-Regular.otf'));
      await icons.load();
      final groups = FontLoader('DeviceGroup')
        ..addFont(rootBundle.load('assets/device_group.ttf'));
      await groups.load();
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
    final boundary = boundaryKey.currentContext!.findRenderObject()!
        as RenderRepaintBoundary;
    final rootPaints = boundary.debugSymmetricPaintCount;
    final particlePaints = panel.field.particlePaints;
    final settledPaints = panel.field.settledPaints;
    panel.field.interactive = false;
    await tester.pump(const Duration(milliseconds: 50));
    expect(panel.field.particlePaints, greaterThan(particlePaints));
    expect(panel.field.settledPaints, settledPaints);
    expect(boundary.debugSymmetricPaintCount, rootPaints);
    panel.field.interactive = true;
    tester.binding.handleAppLifecycleStateChanged(AppLifecycleState.inactive);
    final inactiveFrames = panel.field.renderedFrames;
    await tester.pump(const Duration(milliseconds: 200));
    expect(panel.field.renderedFrames, greaterThan(inactiveFrames));
    final hiddenFrames = panel.field.renderedFrames;
    tester.binding.handleAppLifecycleStateChanged(AppLifecycleState.hidden);
    await tester.pump(const Duration(milliseconds: 200));
    expect(panel.field.renderedFrames, hiddenFrames);
    tester.binding.handleAppLifecycleStateChanged(AppLifecycleState.resumed);
    await tester.pump(const Duration(milliseconds: 50));
    expect(panel.field.renderedFrames, greaterThan(inactiveFrames));
    final floorBefore = List<double>.of(panel.field.floor);
    expect(panel.field.columns.expand((c) => c).map((l) => l.band).toSet(),
        containsAll([10, 11, 12, 13, 14, 15]));
    final origin = tester.getTopLeft(find.byType(SnowPanel));
    final mouse = await tester.createGesture(kind: ui.PointerDeviceKind.mouse);
    await mouse.down(origin + Offset(20, panel.field.size.height - 8));
    await mouse.moveTo(origin +
        Offset(panel.field.size.width - 12, panel.field.size.height - 8));
    await mouse.up();
    expect(panel.field.floor, isNot(equals(floorBefore)));
    expect(panel.field.debrisCount, lessThanOrEqualTo(SnowField.maxDebris));
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
    await tester.tap(find.text('Настройки').first);
    await tester.pump(const Duration(milliseconds: 200));
    final hex = find.byWidgetPredicate((widget) =>
        widget is TextField && widget.decoration?.labelText == 'Цвет HEX');
    await tester.enterText(hex, '#DCE5ED');
    await tester.pump();
    expect(tester.widget<SnowPanel>(find.byType(SnowPanel)).lightBackground,
        const Color(0xffdce5ed));
    await tester.tap(find.text('Готово'));
    await tester.pump(const Duration(milliseconds: 300));
    await tester.tap(find.byTooltip('Настройки стенда'));
    await tester.pump(const Duration(milliseconds: 200));
    expect(find.byType(AlertDialog), findsOneWidget);
    await tester.tap(find.text('Готово'));
    await tester.pump(const Duration(milliseconds: 300));
    expect(tester.takeException(), isNull);
    await tester.tap(find.text('30').first);
    await tester.pump(const Duration(milliseconds: 200));
    await tester.tap(find.text('45').last);
    await tester.pump(const Duration(milliseconds: 200));
    expect(
        tester.widget<SnowPanel>(find.byType(SnowPanel)).framesPerSecond, 45);
    await tester.tap(find.text('Лёгкий снег'));
    await tester.pump();
    expect(tester.widget<SnowPanel>(find.byType(SnowPanel)).lightweight, false);
    await tester.tap(find.text('Пакетные снежинки'));
    await tester.pump();
    expect(tester.widget<SnowPanel>(find.byType(SnowPanel)).batched, true);
    await tester.tap(find.text('45').first);
    await tester.pump(const Duration(milliseconds: 200));
    await tester.tap(find.text('60').last);
    await tester.pump(const Duration(milliseconds: 200));
    expect(
        tester.widget<SnowPanel>(find.byType(SnowPanel)).framesPerSecond, 60);
    await tester.tap(find.text('Продолжить'));
    await tester.pump(const Duration(milliseconds: 50));
    await tester.tap(find.text('Пустое окно'));
    await tester.pump();
    expect(find.byType(SnowPanel), findsNothing);
    final framesBefore = panel.field.renderedFrames;
    await tester.pump(const Duration(seconds: 2));
    expect(panel.field.renderedFrames, framesBefore);
    await tester.pumpWidget(const SizedBox.shrink());
  });
}
