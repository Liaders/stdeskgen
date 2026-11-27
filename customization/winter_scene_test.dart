import 'dart:typed_data';
import 'dart:io';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'winter_scene.dart';

class _WinterAssets extends CachingAssetBundle {
  @override
  Future<ByteData> load(String key) async {
    if (key.startsWith('assets/rdgen-winter-')) {
      final name = key.substring('assets/'.length);
      return ByteData.sublistView(
          await File('../customization/winter_assets/$name').readAsBytes());
    }
    return rootBundle.load(key);
  }
}

void main() {
  testWidgets(
      'client winter art stays behind scrollable controls and fades on resize',
      (tester) async {
    tester.binding.handleAppLifecycleStateChanged(AppLifecycleState.resumed);
    final scroll = ScrollController();
    final contentKey = GlobalKey();
    var taps = 0;
    Widget scene(double height) => MaterialApp(
        home: Scaffold(
            body: DefaultAssetBundle(
                bundle: _WinterAssets(),
                child: Align(
                  alignment: Alignment.topLeft,
                  child: SizedBox(
                      width: 200,
                      height: height,
                      child: RdgenWinterScene(
                        contentKey: contentKey,
                        scrollController: scroll,
                        child: SingleChildScrollView(
                            controller: scroll,
                            child: SizeChangedLayoutNotifier(
                                child: Column(
                              key: contentKey,
                              children: [
                                const SizedBox(height: 300),
                                SizedBox(
                                    height: 40,
                                    child: TextButton(
                                        onPressed: () => taps++,
                                        child: const Text('Controls')))
                              ],
                            ))),
                      )),
                ))));
    await tester.pumpWidget(scene(600));
    await tester.pump();
    LinearGradient fade() => (tester
        .widgetList<DecoratedBox>(find.byType(DecoratedBox))
        .map((widget) => widget.decoration)
        .whereType<BoxDecoration>()
        .map((decoration) => decoration.gradient)
        .whereType<LinearGradient>()
        .single);
    final initialStart = fade().stops![1];
    expect(initialStart, closeTo(340 / 600, 0.001));
    await tester.tap(find.text('Controls'));
    expect(taps, 1);
    await tester.pumpWidget(scene(380));
    await tester.pump();
    expect(fade().stops![1], greaterThan(initialStart));
    await tester.pumpWidget(scene(240));
    await tester.pump();
    scroll.jumpTo(100);
    await tester.pump();
    await tester.pump();
    await tester.tap(find.text('Controls'));
    expect(taps, 2);
    expect(tester.takeException(), isNull);
    await tester.pumpWidget(const SizedBox());
    scroll.dispose();
  });
}
