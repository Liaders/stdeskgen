import 'package:flutter/widgets.dart';

class RdgenDeviceOrganizationOrigin extends InheritedWidget {
  const RdgenDeviceOrganizationOrigin({super.key, required super.child});
  static bool of(BuildContext context) => context.dependOnInheritedWidgetOfExactType<RdgenDeviceOrganizationOrigin>() != null;
  @override
  bool updateShouldNotify(RdgenDeviceOrganizationOrigin oldWidget) => false;
}
