import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_hbb/common/widgets/rdgen_resizable_panel.dart';

void main() {
  Widget panel(String Function() read, Future<void> Function(String) save,
      {double available = 800, Key? key}) => MaterialApp(home: Align(
        alignment: Alignment.topLeft,
        child: SizedBox(width: available, height: 200, child: RdgenResizablePanel(key: key,
          initialWidth: 200, availableWidth: available, readWidth: read,
          saveWidth: save, restoreLabel: 'Restore',
          builder: (width) => SizedBox(key: const ValueKey('content'), width: width))),
      ));

  testWidgets('Drag changes width and restores it after remount', (tester) async {
    String saved = '';
    await tester.pumpWidget(panel(() => saved, (value) async {saved = value;}));
    await tester.drag(find.byKey(const ValueKey('rdgen-panel-handle')), const Offset(100, 0));
    await tester.pumpAndSettle();
    final width = tester.getSize(find.byKey(const ValueKey('content'))).width;
    expect(width, greaterThan(200));
    expect(double.parse(saved), closeTo(width, 1));
    await tester.pumpWidget(const SizedBox());
    await tester.pumpWidget(panel(() => saved, (value) async {saved = value;}));
    expect(tester.getSize(find.byKey(const ValueKey('content'))).width, closeTo(width, 1));
  });

  testWidgets('Narrow windows constrain the panel without replacing preference', (tester) async {
    String saved = '320';
    await tester.pumpWidget(panel(() => saved, (value) async {saved = value;}, available: 300));
    expect(tester.getSize(find.byKey(const ValueKey('content'))).width, lessThan(150));
    expect(saved, '320');
    await tester.pumpWidget(panel(() => saved, (value) async {saved = value;}, available: 800));
    expect(tester.getSize(find.byKey(const ValueKey('content'))).width, 320);
    expect(tester.takeException(), isNull);
  });

  testWidgets('Double click restores configured initial width', (tester) async {
    String saved = '300';
    await tester.pumpWidget(panel(() => saved, (value) async {saved = value;}));
    final handle = find.byKey(const ValueKey('rdgen-panel-handle'));
    await tester.tap(handle);
    await tester.pump(const Duration(milliseconds: 80));
    await tester.tap(handle);
    await tester.pumpAndSettle();
    expect(saved, '');
    expect(tester.getSize(find.byKey(const ValueKey('content'))).width, 200);
  });
}
