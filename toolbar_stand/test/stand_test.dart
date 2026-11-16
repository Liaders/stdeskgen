import 'dart:io';
import 'dart:ui' as ui;
import 'package:flutter/rendering.dart';
import 'package:flutter/services.dart';
import 'package:flutter/material.dart';
import 'package:statusdesk_toolbar_stand/models/rdgen_compact_session_toolbar.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:statusdesk_toolbar_stand/main.dart';

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
  final image =
      await (key.currentContext!.findRenderObject() as RenderRepaintBoundary)
          .toImage();
  final bytes = await image.toByteData(format: ui.ImageByteFormat.png);
  File('$dir/$name.png').writeAsBytesSync(bytes!.buffer.asUint8List());
  image.dispose();
}

void main() {
  testWidgets('Pulse stays readable and stops after assignment',
      (tester) async {
    Widget host(bool active) => MaterialApp(
        home: RdgenOrganizationPulse(
            active: active, child: const Text('Назначить организацию')));
    await tester.pumpWidget(host(true));
    await tester.pump(const Duration(milliseconds: 900));
    final fade =
        tester.widget<FadeTransition>(find.byType(FadeTransition).first);
    expect(fade.opacity.value, closeTo(.58, .01));
    await tester.pumpWidget(host(false));
    await tester.pumpAndSettle();
    expect(
        tester
            .widget<FadeTransition>(find.byType(FadeTransition).first)
            .opacity
            .value,
        1);
    await tester.pumpWidget(const SizedBox());
  });
  testWidgets(
      'Organization and monitor states work at desktop and narrow widths',
      (tester) async {
    tester.view.physicalSize = const Size(1280, 800);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    tester.binding.platformDispatcher.accessibilityFeaturesTestValue =
        const FakeAccessibilityFeatures(disableAnimations: true);
    addTearDown(
        tester.binding.platformDispatcher.clearAccessibilityFeaturesTestValue);
    await tester.runAsync(fonts);
    final imageKey = GlobalKey();
    await tester.pumpWidget(
        RepaintBoundary(key: imageKey, child: const ToolbarStand()));
    await tester.pumpAndSettle();
    expect(find.text('1/3'), findsOneWidget);
    await tester.tap(find.text('Выбрать организацию'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Узорметалл'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Переподключиться'));
    await tester.pumpAndSettle();
    expect(find.text('Узорметалл'), findsOneWidget);
    await tester.tap(find.byTooltip('Выбрать монитор'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Монитор 2'));
    await tester.pumpAndSettle();
    expect(find.text('2/3'), findsOneWidget);
    await tester.tap(find.byTooltip('Свернуть'));
    await tester.pumpAndSettle();
    expect(find.byIcon(Icons.keyboard_arrow_down), findsOneWidget);
    await tester.tap(find.byIcon(Icons.keyboard_arrow_down));
    await tester.pumpAndSettle();
    expect(find.text('2/3'), findsOneWidget);
    await tester
        .tap(find.widgetWithText(SwitchListTile, 'Организация выбрана'));
    await tester.pumpAndSettle();
    expect(find.text('Назначить организацию'), findsOneWidget);
    expect(
        tester
            .getSize(find.widgetWithText(TextButton, 'Назначить организацию'))
            .height,
        30);
    expect(tester.getSize(find.byTooltip('Выбрать монитор')).height, 30);
    expect(
        tester.getSize(find.byTooltip('Завершить тестовый сеанс')).height, 30);
    final label = tester.widget<Text>(find.text('Назначить организацию'));
    expect(label.overflow, TextOverflow.visible);
    if (Platform.environment['RDGEN_PREVIEW_DIR'] != null) {
      await tester.runAsync(() async {
        final image = await (imageKey.currentContext!.findRenderObject()
                as RenderRepaintBoundary)
            .toImage();
        final bytes = await image.toByteData(format: ui.ImageByteFormat.png);
        final dir = Directory(Platform.environment['RDGEN_PREVIEW_DIR']!)
          ..createSync(recursive: true);
        File('${dir.path}/toolbar-refined.png')
            .writeAsBytesSync(bytes!.buffer.asUint8List());
        image.dispose();
      });
    }
    await tester.tap(find.byTooltip('Параметры изображения'));
    await tester.pumpAndSettle();
    await tester.pump(const Duration(seconds: 3));
    expect(find.text('Качество изображения'), findsOneWidget);
    expect(
        tester
            .getSize(find.widgetWithText(MenuItemButton, 'Подогнать окно'))
            .height,
        28);
    expect(
        tester
            .renderObject<RenderParagraph>(find.text('Подогнать окно'))
            .text
            .style
            ?.fontWeight,
        FontWeight.w400);
    if (Platform.environment['RDGEN_PREVIEW_DIR'] != null) {
      await tester.runAsync(() async {
        final image = await (imageKey.currentContext!.findRenderObject()
                as RenderRepaintBoundary)
            .toImage();
        final bytes = await image.toByteData(format: ui.ImageByteFormat.png);
        File('${Platform.environment['RDGEN_PREVIEW_DIR']}/toolbar-menu.png')
            .writeAsBytesSync(bytes!.buffer.asUint8List());
        image.dispose();
      });
    }
    await tester.tap(find.text('Кодек'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('AV1'));
    await tester.pumpAndSettle();
    expect(find.text('Демонстрация: Кодек — AV1'), findsOneWidget);
    await tester.tap(find.byTooltip('Ещё'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Запись сеанса'));
    await tester.pumpAndSettle();
    expect(find.text('Демонстрация: запись включена'), findsOneWidget);
    tester.view.physicalSize = const Size(650, 600);
    await tester.pumpAndSettle();
    expect(tester.takeException(), isNull);
    await tester.pumpWidget(
        const MaterialApp(home: RdgenDisplayCounter(current: 0, total: 1)));
    expect(find.text('1/1'), findsNothing);
    await tester.pumpWidget(const SizedBox());
  });
  testWidgets(
      'Create, auto-select and reconnect keep distinct session organizations',
      (tester) async {
    tester.view.physicalSize = const Size(1280, 800);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    tester.binding.platformDispatcher.accessibilityFeaturesTestValue =
        const FakeAccessibilityFeatures(disableAnimations: true);
    addTearDown(
        tester.binding.platformDispatcher.clearAccessibilityFeaturesTestValue);
    await tester.pumpWidget(const ToolbarStand());
    await tester.pumpAndSettle();
    await tester
        .tap(find.widgetWithText(SwitchListTile, 'Устройство без организаций'));
    await tester.pumpAndSettle();
    await tester.tap(find.byTooltip('Организация сеанса'));
    await tester.pumpAndSettle();
    expect(find.byType(AlertDialog), findsOneWidget);
    expect(find.text('Назначить организацию…'), findsNothing);
    expect(find.byKey(const ValueKey('device-alias')), findsOneWidget);
    await tester.enterText(
        find.byKey(const ValueKey('device-alias')), 'Бухгалтерия — Анна');
    await tester.enterText(
        find.byKey(const ValueKey('organization-search')), 'Новая компания');
    await tester.pumpAndSettle();
    expect(find.text('Организации не найдены'), findsOneWidget);
    await tester.tap(find.byKey(const ValueKey('create-organization')));
    await tester.pumpAndSettle();
    expect(tester.widget<CheckboxListTile>(find.byType(CheckboxListTile)).value,
        true);
    expect(
        tester
            .widget<TextField>(
                find.byKey(const ValueKey('new-organization-name')))
            .controller!
            .text,
        'Новая компания');
    expect(find.text('Создать и назначить'), findsOneWidget);
    await tester.tap(find.byKey(const ValueKey('confirm-create-organization')));
    await tester.pumpAndSettle();
    expect(find.text('Назначить организацию устройству?'), findsOneWidget);
    expect(find.text('Устройство: DESKTOP-DEMO'), findsOneWidget);
    await tester.tap(find.text('Назначить'));
    await tester.pumpAndSettle();
    expect(find.text('Новая компания'), findsOneWidget);
    expect(find.textContaining('сеанс №1 — Новая компания'), findsOneWidget);
    expect(find.text('Устройство: Бухгалтерия — Анна'), findsOneWidget);
    await tester.tap(find.byTooltip('Организация сеанса'));
    await tester.pumpAndSettle();
    expect(find.text('Новая компания'), findsNWidgets(2));
    await tester.tap(find.text('Назначить организацию…'));
    await tester.pumpAndSettle();
    expect(find.byKey(const ValueKey('device-alias')), findsNothing);
    await tester.enterText(
        find.byKey(const ValueKey('organization-search')), 'узор');
    await tester.pumpAndSettle();
    await tester.tap(find.text('Узорметалл'));
    await tester.pumpAndSettle();
    expect(
        find.text('Переподключиться к этому устройству по другой организации?'),
        findsOneWidget);
    await tester.tap(find.text('Отмена'));
    await tester.pumpAndSettle();
    expect(find.text('Новая компания'), findsOneWidget);
    await tester.tap(find.byTooltip('Организация сеанса'));
    await tester.pumpAndSettle();
    expect(find.text('Узорметалл'), findsNothing);
    await tester.tap(find.text('Назначить организацию…'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Узорметалл'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Переподключиться'));
    await tester.pumpAndSettle();
    expect(find.textContaining('сеанс №2 — Узорметалл'), findsOneWidget);
    await tester.pumpWidget(const SizedBox());
  });

  testWidgets(
      'Empty device opens assignment directly; alias is optional and cancelled drafts are discarded',
      (tester) async {
    tester.view.physicalSize = const Size(1280, 800);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    tester.binding.platformDispatcher.accessibilityFeaturesTestValue =
        const FakeAccessibilityFeatures(disableAnimations: true);
    addTearDown(
        tester.binding.platformDispatcher.clearAccessibilityFeaturesTestValue);
    await tester.runAsync(fonts);
    final key = GlobalKey();
    await tester
        .pumpWidget(RepaintBoundary(key: key, child: const ToolbarStand()));
    await tester.pumpAndSettle();
    await tester
        .tap(find.widgetWithText(SwitchListTile, 'Устройство без организаций'));
    await tester.pumpAndSettle();
    await tester.tap(find.byTooltip('Организация сеанса'));
    await tester.pumpAndSettle();
    await tester.enterText(
        find.byKey(const ValueKey('device-alias')), 'Бухгалтерия — Анна');
    await tester.pumpAndSettle();
    if (Platform.environment['RDGEN_PREVIEW_DIR'] != null) {
      await tester.runAsync(() async {
        final image = await (key.currentContext!.findRenderObject()
                as RenderRepaintBoundary)
            .toImage();
        final bytes = await image.toByteData(format: ui.ImageByteFormat.png);
        File('${Platform.environment['RDGEN_PREVIEW_DIR']}/toolbar-first-assignment.png')
            .writeAsBytesSync(bytes!.buffer.asUint8List());
        image.dispose();
      });
    }
    await tester.tap(find.text('Отмена'));
    await tester.pumpAndSettle();
    expect(find.text('Устройство: DESKTOP-DEMO'), findsOneWidget);
    await tester.tap(find.byTooltip('Организация сеанса'));
    await tester.pumpAndSettle();
    expect(
        tester
            .widget<TextField>(find.byKey(const ValueKey('device-alias')))
            .controller!
            .text,
        isEmpty);
    await tester.tap(find.text('Узорметалл'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Назначить'));
    await tester.pumpAndSettle();
    expect(find.text('Устройство: DESKTOP-DEMO'), findsOneWidget);
    await tester
        .tap(find.widgetWithText(SwitchListTile, 'Устройство без организаций'));
    await tester.pumpAndSettle();
    await tester
        .tap(find.widgetWithText(SwitchListTile, 'Псевдоним уже задан'));
    await tester.pumpAndSettle();
    await tester.tap(find.byTooltip('Организация сеанса'));
    await tester.pumpAndSettle();
    expect(find.byKey(const ValueKey('organization-search')), findsOneWidget);
    expect(find.byKey(const ValueKey('device-alias')), findsNothing);
    await tester.tap(find.text('Отмена'));
    await tester.pumpAndSettle();
    await tester.pumpWidget(const SizedBox());
  });

  testWidgets(
      'Standalone alias and create-only do not change the session or device bindings',
      (tester) async {
    tester.view.physicalSize = const Size(1280, 800);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    tester.binding.platformDispatcher.accessibilityFeaturesTestValue =
        const FakeAccessibilityFeatures(disableAnimations: true);
    addTearDown(
        tester.binding.platformDispatcher.clearAccessibilityFeaturesTestValue);
    await tester.runAsync(fonts);
    final key = GlobalKey();
    await tester
        .pumpWidget(RepaintBoundary(key: key, child: const ToolbarStand()));
    await tester.pumpAndSettle();
    await tester.tap(find.byTooltip('Организация сеанса'));
    await tester.pumpAndSettle();
    await tester.runAsync(() => standSnapshot(key, 'toolbar-alias-menu'));
    await tester.tap(find.text('Назначить псевдоним устройства'));
    await tester.pumpAndSettle();
    await tester.enterText(
        find.byKey(const ValueKey('standalone-device-alias')), 'Бухгалтерия');
    await tester.tap(find.text('Сохранить'));
    await tester.pumpAndSettle();
    expect(find.text('Устройство: Бухгалтерия'), findsOneWidget);
    await tester.tap(find.byTooltip('Организация сеанса'));
    await tester.pumpAndSettle();
    expect(find.text('Назначить псевдоним устройства'), findsNothing);
    await tester.tap(find.text('Назначить организацию…'));
    await tester.pumpAndSettle();
    await tester.enterText(
        find.byKey(const ValueKey('organization-search')), 'Только создать');
    await tester.tap(find.byKey(const ValueKey('create-organization')));
    await tester.pumpAndSettle();
    await tester.runAsync(() => standSnapshot(key, 'toolbar-create-options'));
    await tester.tap(find.byKey(const ValueKey('create-only-organization')));
    await tester.pumpAndSettle();
    expect(
        find.text(
            'Организация «Только создать» создана без назначения устройству.'),
        findsOneWidget);
    expect(
        find.text('Переподключиться к этому устройству по другой организации?'),
        findsNothing);
    await tester.tap(find.byTooltip('Организация сеанса'));
    await tester.pumpAndSettle();
    expect(find.text('Только создать'), findsNothing);
    await tester.tap(find.text('Назначить организацию…'));
    await tester.pumpAndSettle();
    await tester.enterText(
        find.byKey(const ValueKey('organization-search')), 'Только создать');
    await tester.pumpAndSettle();
    await tester.tap(find.widgetWithText(ListTile, 'Только создать'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Отмена'));
    await tester.pumpAndSettle();
    await tester.tap(find.byTooltip('Организация сеанса'));
    await tester.pumpAndSettle();
    expect(find.text('Только создать'), findsNothing);
    expect(find.text('Организация Статус'), findsNWidgets(2));
    await tester.pumpWidget(const SizedBox());
  });
}
