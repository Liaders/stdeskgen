import 'dart:io';
import 'dart:ui' as ui;
import 'package:flutter/rendering.dart';
import 'package:flutter/services.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:statusdesk_toolbar_stand/main.dart';
import 'package:flutter_svg/flutter_svg.dart';

Future<void> fonts() async {
  for (final entry in {
    'Roboto': 'Roboto-Regular.ttf',
    'MaterialIcons': 'MaterialIcons-Regular.otf'
  }.entries) {
    final bytes =
        File('C:/src/flutter/bin/cache/artifacts/material_fonts/${entry.value}')
            .readAsBytesSync();
    final loader = FontLoader(entry.key)
      ..addFont(Future.value(ByteData.sublistView(bytes)));
    await loader.load();
  }
}

Future<void> standSnapshot(GlobalKey key, String name) async {
  final dir = Platform.environment['RDGEN_PREVIEW_DIR'];
  if (dir == null) return;
  Directory(dir).createSync(recursive: true);
  final image =
      await (key.currentContext!.findRenderObject() as RenderRepaintBoundary)
          .toImage();
  final bytes = await image.toByteData(format: ui.ImageByteFormat.png);
  File('$dir/$name.png').writeAsBytesSync(bytes!.buffer.asUint8List());
  image.dispose();
}

void main() {
  testWidgets(
      'Current production geometry supports SVG and original icons at desktop scales',
      (tester) async {
    tester.binding.platformDispatcher.accessibilityFeaturesTestValue =
        const FakeAccessibilityFeatures(disableAnimations: true);
    addTearDown(
        tester.binding.platformDispatcher.clearAccessibilityFeaturesTestValue);
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    await tester.runAsync(fonts);
    for (final scale in [1.0, 1.25, 1.5]) {
      tester.view.devicePixelRatio = scale;
      tester.view.physicalSize = Size(1280 * scale, 900 * scale);
      final key = GlobalKey();
      await tester
          .pumpWidget(RepaintBoundary(key: key, child: const ToolbarStand()));
      await tester.pumpAndSettle();
      expect(find.byType(SvgPicture), findsWidgets);
      expect(tester.getSize(find.byTooltip('Закрепить панель')),
          const Size(30, 30));
      expect(tester.getSize(find.byTooltip('Завершить тестовый сеанс')),
          const Size(30, 30));
      await tester.runAsync(
          () => standSnapshot(key, 'toolbar-dark-$scale'));
      final theme = find.widgetWithText(SwitchListTile, 'Тёмная тема сеанса');
      await tester.ensureVisible(theme);
      await tester.tap(theme);
      await tester.pumpAndSettle();
      await tester.runAsync(
          () => standSnapshot(key, 'toolbar-light-$scale'));
      final svg = find.widgetWithText(SwitchListTile, 'Новые SVG-иконки');
      await tester.ensureVisible(svg);
      await tester.tap(svg);
      await tester.pumpAndSettle();
      expect(find.byType(SvgPicture), findsNothing);
      expect(tester.takeException(), isNull);
      await tester.pumpWidget(const SizedBox());
    }
  });

  testWidgets('Organization choice and native-style More icons stay available',
      (tester) async {
    tester.view.physicalSize = const Size(1280, 900);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    tester.binding.platformDispatcher.accessibilityFeaturesTestValue =
        const FakeAccessibilityFeatures(disableAnimations: true);
    addTearDown(
        tester.binding.platformDispatcher.clearAccessibilityFeaturesTestValue);
    await tester.pumpWidget(const ToolbarStand());
    await tester.pumpAndSettle();
    await tester.tap(find.text('Выбрать организацию'));
    await tester.pumpAndSettle();
    expect(find.text('Выберите организацию'), findsOneWidget);
    expect(find.text('Создать организацию'), findsNothing);
    await tester.tap(find.text('Узорметалл'));
    await tester.tap(find.text('Подтвердить'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Переподключиться'));
    await tester.pumpAndSettle();
    expect(find.textContaining('сеанс №2 — Узорметалл'), findsOneWidget);
    await tester.tap(find.byTooltip('Ещё'));
    await tester.pumpAndSettle();
    expect(find.byTooltip('Чат'), findsOneWidget);
    expect(find.byTooltip('Запись сеанса'), findsOneWidget);
    await tester.tap(find.byTooltip('Запись сеанса'));
    await tester.pumpAndSettle();
    expect(find.text('Демонстрация: запись включена'), findsOneWidget);
    expect(tester.takeException(), isNull);
    await tester.pumpWidget(const SizedBox());
  });
}
