import 'dart:io';
import 'dart:ui' as ui;
import 'dart:typed_data';
import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import '../lib/models/rdgen_compact_session_toolbar.dart';

Widget actions() => Row(mainAxisSize: MainAxisSize.min, children: [
  IconButton(onPressed: () {}, icon: const Icon(Icons.push_pin_outlined)),
  RdgenOrganizationToolbarButton(name: 'Организация Статус', onPressed: () {}),
  TextButton.icon(onPressed: () {}, icon: const Icon(Icons.desktop_windows_outlined), label: const Text('1/3')),
  ...[Icons.mouse_outlined, Icons.settings_outlined, Icons.keyboard_outlined,
      Icons.call_outlined, Icons.more_horiz, Icons.close].map((icon) =>
      IconButton(onPressed: () {}, icon: Icon(icon, size: 20))),
]);

Future<void> preview(GlobalKey key, String name) async {
  final directory = Platform.environment['RDGEN_PREVIEW_DIR'];
  if (directory == null) return;
  final boundary = key.currentContext!.findRenderObject() as RenderRepaintBoundary;
  final image = await boundary.toImage(pixelRatio: 1);
  final bytes = await image.toByteData(format: ui.ImageByteFormat.png);
  Directory(directory).createSync(recursive: true);
  File('$directory/$name.png').writeAsBytesSync(bytes!.buffer.asUint8List());
}

Future<void> loadPreviewFonts() async {
  final sdk = Platform.environment['FLUTTER_ROOT'] ??
      File((Process.runSync('which', ['flutter']).stdout as String).trim())
          .resolveSymbolicLinksSync().replaceFirst(RegExp(r'/bin/flutter$'), '');
  for (final entry in {'Roboto': 'Roboto-Regular.ttf', 'MaterialIcons': 'MaterialIcons-Regular.otf'}.entries) {
    final bytes = await File('$sdk/bin/cache/artifacts/material_fonts/${entry.value}').readAsBytes();
    final loader = FontLoader(entry.key)..addFont(Future.value(ByteData.sublistView(bytes)));
    await loader.load();
  }
}

void main() {
  testWidgets('Only visible return controls intercept input and their drag stays in the window', (tester) async {
    await tester.runAsync(loadPreviewFonts);
    var remoteClicks = 0;
    var expanded = 0;
    var chosen = 0;
    final key = GlobalKey();
    Widget host(bool collapsed, bool assigned) => MaterialApp(home: Scaffold(body:
      RepaintBoundary(key: key, child: Stack(children: [
        Positioned.fill(child: GestureDetector(onTap: () { remoteClicks++; },
          child: Container(color: const Color(0xff14202c), alignment: Alignment.center,
            child: const Text('Удалённый рабочий стол', style: TextStyle(color: Colors.white38, fontSize: 24))))),
        Positioned.fill(child: RdgenCompactSessionToolbar(key: ValueKey('$collapsed/$assigned'), collapsed: collapsed, assigned: assigned,
          organization: assigned ? 'Организация Статус' : null,
          onExpand: () { expanded++; }, onChoose: () { chosen++; }, child: actions())),
      ]))));
    await tester.pumpWidget(host(true, true));
    await tester.pumpAndSettle();
    await tester.runAsync(() => preview(key, 'toolbar-collapsed-assigned'));
    await tester.tapAt(const Offset(10, 4));
    expect(remoteClicks, 1);
    final handle = find.byIcon(Icons.keyboard_arrow_down);
    await tester.drag(handle, const Offset(2000, 0));
    await tester.pumpAndSettle();
    final rectangle = tester.getRect(handle);
    expect(rectangle.left, greaterThanOrEqualTo(0));
    expect(rectangle.right, lessThanOrEqualTo(800));
    await tester.tap(handle);
    await tester.pumpAndSettle();
    expect(expanded, 1);
    await tester.pumpWidget(host(true, false));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Assign organization'));
    expect(chosen, 1);
    await tester.tap(handle);
    await tester.pumpAndSettle();
    expect(expanded, 2);
    await tester.runAsync(() => preview(key, 'toolbar-collapsed-unassigned'));
    await tester.pumpWidget(host(false, true));
    await tester.pumpAndSettle();
    expect(find.byIcon(Icons.push_pin_outlined), findsOneWidget);
    expect(find.text('1/3'), findsOneWidget);
    expect(tester.takeException(), isNull);
    await tester.runAsync(() => preview(key, 'toolbar-expanded'));
  });
}
