import 'package:flutter/material.dart';
import 'package:flutter_svg/flutter_svg.dart';

class StandIconStyle extends InheritedWidget {
  final bool svg;
  const StandIconStyle({super.key, required this.svg, required super.child});
  static bool enabled(BuildContext context) =>
      context.dependOnInheritedWidgetOfExactType<StandIconStyle>()?.svg ?? true;
  @override
  bool updateShouldNotify(StandIconStyle oldWidget) => svg != oldWidget.svg;
}

class StandToolbarIcon extends StatelessWidget {
  final String kind;
  final Color color;
  final Widget fallback;
  const StandToolbarIcon(this.kind,
      {super.key, required this.color, required this.fallback});
  @override
  Widget build(BuildContext context) => StandIconStyle.enabled(context)
      ? SizedBox(
          width: 22,
          height: 22,
          child: Center(
              child: SvgPicture.asset('assets/icons/$kind.svg',
                  width: 20,
                  height: 20,
                  colorFilter: ColorFilter.mode(color, BlendMode.srcIn))))
      : (kind == 'chat' || kind == 'record')
          ? SizedBox(width: 22, height: 22, child: Icon(
              kind == 'chat' ? Icons.chat_bubble_outline : Icons.fiber_manual_record,
              size: 20, color: color))
          : fallback;
}
