import 'package:flutter/gestures.dart';
import 'package:flutter/material.dart';

class RdgenTabDragListener extends ReorderableDragStartListener {
  final VoidCallback activate;
  const RdgenTabDragListener({super.key, required super.index, required super.child, required this.activate});
  @override
  Widget build(BuildContext context) => Listener(
    onPointerDown: (event) { if (event.buttons == kPrimaryButton) activate(); },
    child: super.build(context));
  @override
  MultiDragGestureRecognizer createRecognizer() => _TabDragRecognizer(debugOwner: this);
}
class _TabDragRecognizer extends ImmediateMultiDragGestureRecognizer {
  _TabDragRecognizer({super.debugOwner});
  @override
  MultiDragPointerState createNewPointerState(PointerDownEvent event) =>
      _TabPointerState(event.position, event.kind, gestureSettings);
}
class _TabPointerState extends MultiDragPointerState {
  _TabPointerState(super.initialPosition, super.kind, super.gestureSettings);
  GestureMultiDragStartCallback? _starter;
  @override
  void checkForResolutionAfterMove() {
    if ((pendingDelta?.distance ?? 0) > 10) {
      final starter = _starter;
      if (starter != null) { _starter = null; starter(initialPosition); }
      else { resolve(GestureDisposition.accepted); }
    }
  }
  @override
  void accepted(GestureMultiDragStartCallback starter) {
    if ((pendingDelta?.distance ?? 0) > 10) starter(initialPosition);
    else { _starter = starter; }
  }
}
