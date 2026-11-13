import 'dart:async';
import 'package:flutter/widgets.dart';

const rdgenWorkGroupZoneKey = #statusdeskWorkGroupOrigin;

class RdgenWorkGroupOrigin extends InheritedWidget {
  final int groupId;
  const RdgenWorkGroupOrigin({super.key, required this.groupId, required super.child});

  // Non-listening lookup is also safe during a session page's initState.
  static int? read(BuildContext context) =>
      (context.getElementForInheritedWidgetOfExactType<RdgenWorkGroupOrigin>()?.widget
          as RdgenWorkGroupOrigin?)?.groupId;

  @override
  bool updateShouldNotify(RdgenWorkGroupOrigin oldWidget) => oldWidget.groupId != groupId;
}

Widget rdgenWorkGroupPage(dynamic args, Widget child) {
  final id = args is Map ? args['rdgen_work_group_id'] : null;
  return id is int && id > 0 ? RdgenWorkGroupOrigin(groupId: id, child: child) : child;
}

int? get rdgenLaunchingWorkGroup => Zone.current[rdgenWorkGroupZoneKey] as int?;
