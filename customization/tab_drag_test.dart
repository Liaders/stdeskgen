import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'tab_drag.dart';
void main() {
 testWidgets('press activates; diagonal distance must exceed ten before drag', (tester) async {
  var active=false, started=0;
  await tester.pumpWidget(MaterialApp(home: Scaffold(body: SizedBox(height:32,
   child: ReorderableListView(scrollDirection:Axis.horizontal,buildDefaultDragHandles:false,
    onReorder:(a,b){},onReorderStart:(_){started++;},children:[
      RdgenTabDragListener(key:const ValueKey(0),index:0,activate:(){active=true;},child:const SizedBox(width:100,child:Text('First'))),
      RdgenTabDragListener(key:const ValueKey(1),index:1,activate:(){},child:const SizedBox(width:100,child:Text('Second'))),
    ])))));
  final pos=tester.getCenter(find.text('First'));
  final gesture=await tester.startGesture(pos);
  expect(active,isTrue);
  await gesture.moveTo(pos+const Offset(7,7));await tester.pump();
  expect(started,0);
  await gesture.moveTo(pos+const Offset(8,8));await tester.pump();
  expect(started,1);
  await gesture.up();await tester.pumpAndSettle();
  expect(tester.takeException(),isNull);
 });
}
