import 'dart:math' as math;
import 'package:flutter/material.dart';
import '../common.dart' show translate;

class RdgenCompactToolbarScope extends InheritedWidget {
  const RdgenCompactToolbarScope({super.key, required super.child});
  static bool active(BuildContext context) =>
      context.dependOnInheritedWidgetOfExactType<RdgenCompactToolbarScope>() != null;
  @override
  bool updateShouldNotify(RdgenCompactToolbarScope oldWidget) => false;
}

class RdgenCompactSessionToolbar extends StatefulWidget {
  final bool collapsed;
  final bool assigned;
  final String? organization;
  final VoidCallback onExpand;
  final VoidCallback onChoose;
  final Widget child;
  const RdgenCompactSessionToolbar({super.key, required this.collapsed,
    required this.assigned, this.organization, required this.onExpand,
    required this.onChoose, required this.child});
  @override
  State<RdgenCompactSessionToolbar> createState() => _RdgenCompactSessionToolbarState();
}

class _RdgenCompactSessionToolbarState extends State<RdgenCompactSessionToolbar> {
  double offset = 0;
  @override
  Widget build(BuildContext context) {
    final dark = ThemeData.dark().copyWith(
      visualDensity: VisualDensity.compact,
      colorScheme: const ColorScheme.dark(primary: Color(0xffef7f1a), surface: Color(0xff22252b)),
      tooltipTheme: const TooltipThemeData(waitDuration: Duration(milliseconds: 500)));
    return Theme(data: dark, child: LayoutBuilder(builder: (context, constraints) {
      final width = math.min(widget.assigned ? 40.0 : 218.0, constraints.maxWidth);
      final limit = math.max(0.0, (constraints.maxWidth - width) / 2);
      final dx = offset.clamp(-limit, limit).toDouble();
      Widget handle = widget.assigned
        ? SizedBox(width: width, height: 16, child: InkWell(onTap: widget.onExpand,
            child: const Icon(Icons.keyboard_arrow_down, size: 16)))
        : SizedBox(width: width, height: 30, child: Row(children: [
            Expanded(child: TextButton(onPressed: widget.onChoose,
              style: TextButton.styleFrom(foregroundColor: const Color(0xffffcb75),
                padding: const EdgeInsets.symmetric(horizontal: 8)),
              child: Text(translate('Assign organization'), maxLines: 1, overflow: TextOverflow.ellipsis))),
            IconButton(onPressed: widget.onExpand, icon: const Icon(Icons.keyboard_arrow_down, size: 18),
              tooltip: translate('Expand toolbar'), constraints: const BoxConstraints.tightFor(width: 28, height: 28),
              padding: EdgeInsets.zero),
          ]));
      handle = GestureDetector(onPanUpdate: (details) {
          setState(() { offset = (dx + details.delta.dx).clamp(-limit, limit).toDouble(); });
        }, child: Material(color: widget.assigned ? const Color(0xff30343c) : const Color(0xff49391f),
          borderRadius: const BorderRadius.vertical(bottom: Radius.circular(6)),
          child: handle));
      return Align(alignment: Alignment.topCenter, child: widget.collapsed
        ? Transform.translate(offset: Offset(dx, 0), child: handle)
        : ConstrainedBox(constraints: BoxConstraints(maxWidth: constraints.maxWidth),
            child: Material(color: const Color(0xff22252b), elevation: 4,
              borderRadius: const BorderRadius.vertical(bottom: Radius.circular(8)),
              child: RdgenCompactToolbarScope(child: widget.child))));
    }));
  }
}

class RdgenOrganizationToolbarButton extends StatelessWidget {
  final String? name;
  final VoidCallback onPressed;
  final int additionalCount;
  const RdgenOrganizationToolbarButton({super.key, this.name, this.additionalCount = 0, required this.onPressed});
  @override
  Widget build(BuildContext context) => ConstrainedBox(
    constraints: const BoxConstraints(maxWidth: 190),
    child: TextButton.icon(onPressed: onPressed,
      style: TextButton.styleFrom(foregroundColor: name == null
          ? const Color(0xffffcb75) : Colors.white,
        padding: const EdgeInsets.symmetric(horizontal: 8), minimumSize: const Size(0, 28)),
      icon: const Icon(Icons.apartment_outlined, size: 16),
      label: Row(mainAxisSize: MainAxisSize.min, children: [
        Flexible(child: Text(name ?? translate('Assign organization'), maxLines: 1, overflow: TextOverflow.ellipsis)),
        if (additionalCount > 0) Padding(padding: const EdgeInsets.only(left: 4),
          child: Text('+$additionalCount', style: const TextStyle(color: Colors.white54, fontSize: 10))),
      ])));
}

class RdgenDisplayCounter extends StatelessWidget {
  final int current;
  final int total;
  const RdgenDisplayCounter({super.key, required this.current, required this.total});
  @override
  Widget build(BuildContext context) => total < 1 ? const SizedBox.shrink() : SizedBox(width: 54,
    child: Row(mainAxisSize: MainAxisSize.min, children: [
      const Icon(Icons.desktop_windows_outlined, color: Colors.white, size: 16),
      const SizedBox(width: 3),
      Text('${current < 0 ? "*" : current + 1}/$total',
        style: const TextStyle(color: Colors.white, fontSize: 11)),
    ]));
}
