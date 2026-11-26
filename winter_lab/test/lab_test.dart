import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:statusdesk_winter_lab/main.dart';

void main() {
  test('particles keep fixed buffers and stay within panel', () {
    final field=SnowField(24);
    final points=field.points;
    for(var i=0;i<10000;i++) { field.advance(1/60,const Size(200,600)); }
    expect(identical(points,field.points),isTrue);
    for(final y in field.y) { expect(y,inInclusiveRange(0,1)); }
    field.dispose();
  });
  testWidgets('timer requests 30 or 60 updates and stops when hidden', (tester) async {
    for (final fps in [30,60]) {
      tester.binding.handleAppLifecycleStateChanged(AppLifecycleState.resumed);
      await tester.pumpWidget(MaterialApp(home: SizedBox(width:200,height:600,
        child: SnowLayer(key:ValueKey(fps),count:16,activeFps:fps,useTimer:true,drawSnow:false))));
      final field=tester.widgetList<CustomPaint>(find.byType(CustomPaint))
        .map((w)=>w.painter).whereType<SnowPainter>().single.field;
      var updates=0;
      field.addListener(()=>updates++);
      await tester.pump(const Duration(seconds:1));
      expect(updates,closeTo(fps,1));
      tester.binding.handleAppLifecycleStateChanged(AppLifecycleState.hidden);
      final before=updates;
      await tester.pump(const Duration(seconds:1));
      expect(updates,before);
      await tester.pumpWidget(const SizedBox());
    }
    tester.binding.handleAppLifecycleStateChanged(AppLifecycleState.resumed);
  });
  testWidgets('modes fit and hidden window stops simulation', (tester) async {
    await tester.pumpWidget(const WinterLab());
    expect(tester.takeException(),isNull);
    await tester.tap(find.text('Только снег'));
    await tester.pump();
    await tester.pump(const Duration(milliseconds:40));
    final painter=tester.widgetList<CustomPaint>(find.byType(CustomPaint))
      .map((w)=>w.painter).whereType<SnowPainter>().single;
    tester.binding.handleAppLifecycleStateChanged(AppLifecycleState.hidden);
    final before=painter.field.y.toList();
    await tester.pump(const Duration(seconds:1));
    expect(painter.field.y.toList(),before);
    tester.binding.handleAppLifecycleStateChanged(AppLifecycleState.resumed);
    await tester.pumpWidget(const SizedBox());
    expect(tester.takeException(),isNull);
  });
}
