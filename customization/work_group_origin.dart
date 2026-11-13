import 'dart:async';
import 'package:flutter/widgets.dart';

const rdgenWorkGroupZoneKey = #statusdeskWorkGroupOrigin;

class RdgenWorkGroupOrigin extends InheritedWidget {
  final int groupId;
  const RdgenWorkGroupOrigin({super.key, required this.groupId, required super.child});

  static int? read(BuildContext context) =>
      (context.getElementForInheritedWidgetOfExactType<RdgenWorkGroupOrigin>()?.widget
          as RdgenWorkGroupOrigin?)?.groupId;

  @override
  bool updateShouldNotify(RdgenWorkGroupOrigin oldWidget) => oldWidget.groupId != groupId;
}

int? get rdgenLaunchingWorkGroup => Zone.current[rdgenWorkGroupZoneKey] as int?;
