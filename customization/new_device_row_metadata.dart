import 'package:flutter/widgets.dart';

/// Metadata occupies native row space before the original device menu.
class RdgenNewDeviceRowMetadata extends InheritedWidget {
  final Widget details;
  const RdgenNewDeviceRowMetadata({super.key, required this.details, required super.child});
  static Widget? of(BuildContext context) => context
      .dependOnInheritedWidgetOfExactType<RdgenNewDeviceRowMetadata>()?.details;
  @override
  bool updateShouldNotify(RdgenNewDeviceRowMetadata oldWidget) => true;
}
