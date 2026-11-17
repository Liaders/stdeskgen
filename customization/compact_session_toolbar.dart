import 'dart:math' as math;
import 'package:flutter/material.dart';
import '../common.dart' show translate;

const rdgenCompactMenuButtonStyle = ButtonStyle(
  textStyle: WidgetStatePropertyAll(TextStyle(fontFamily: 'Roboto', fontSize: 13, height: 1.2, fontWeight: FontWeight.w400)),
  minimumSize: WidgetStatePropertyAll(Size(0, 28)),
  maximumSize: WidgetStatePropertyAll(Size(double.infinity, 28)),
  padding: WidgetStatePropertyAll(EdgeInsets.symmetric(horizontal: 10)),
  visualDensity: VisualDensity.standard,
  tapTargetSize: MaterialTapTargetSize.shrinkWrap,
);
const rdgenCompactMenuStyle = MenuStyle(
  backgroundColor: WidgetStatePropertyAll(Color(0xff262a30)),
  surfaceTintColor: WidgetStatePropertyAll(Colors.transparent),
  shape: WidgetStatePropertyAll(RoundedRectangleBorder(borderRadius: BorderRadius.all(Radius.circular(6)))),
  padding: WidgetStatePropertyAll(EdgeInsets.symmetric(vertical: 5)),
);

bool rdgenToolbarDark(BuildContext context) => Theme.of(context).brightness == Brightness.dark;
Color rdgenToolbarForeground(BuildContext context) => rdgenToolbarDark(context) ? Colors.white : const Color(0xff24272c);
Color rdgenToolbarSurface(BuildContext context) => rdgenToolbarDark(context) ? const Color(0xff22252b) : const Color(0xfff5f6f8);
Color rdgenToolbarAccent(BuildContext context) => rdgenToolbarDark(context) ? const Color(0xffffcb75) : const Color(0xff965000);
MenuStyle rdgenToolbarMenuStyle(BuildContext context) => rdgenCompactMenuStyle.copyWith(
  backgroundColor: WidgetStatePropertyAll(rdgenToolbarSurface(context)));

class RdgenCompactToolbarScope extends InheritedWidget {
  const RdgenCompactToolbarScope({super.key, required super.child});
  static bool active(BuildContext context) =>
      context.dependOnInheritedWidgetOfExactType<RdgenCompactToolbarScope>() !=
      null;
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
  const RdgenCompactSessionToolbar(
      {super.key,
      required this.collapsed,
      required this.assigned,
      this.organization,
      required this.onExpand,
      required this.onChoose,
      required this.child});
  @override
  State<RdgenCompactSessionToolbar> createState() =>
      _RdgenCompactSessionToolbarState();
}

class _RdgenCompactSessionToolbarState
    extends State<RdgenCompactSessionToolbar> {
  double offset = 0;
  @override
  Widget build(BuildContext context) {
    final inherited = Theme.of(context);
    final foreground = rdgenToolbarForeground(context);
    final dark = inherited.copyWith(
        textTheme: inherited.textTheme.apply(bodyColor: foreground, displayColor: foreground),
        iconTheme: inherited.iconTheme.copyWith(color: foreground),
        visualDensity: VisualDensity.standard,
        menuButtonTheme: const MenuButtonThemeData(style: rdgenCompactMenuButtonStyle),
        menuTheme: MenuThemeData(style: rdgenToolbarMenuStyle(context)),
        menuBarTheme: const MenuBarThemeData(style: MenuStyle(
          backgroundColor: WidgetStatePropertyAll(Colors.transparent),
          surfaceTintColor: WidgetStatePropertyAll(Colors.transparent),
          padding: WidgetStatePropertyAll(EdgeInsets.zero), elevation: WidgetStatePropertyAll(0))),
        dividerTheme: const DividerThemeData(space: 9, thickness: 1),
        colorScheme: inherited.colorScheme.copyWith(primary: const Color(0xffef7f1a),
            surface: rdgenToolbarSurface(context), onSurface: foreground),
        tooltipTheme:
            const TooltipThemeData(waitDuration: Duration(milliseconds: 500)));
    return Theme(
        data: dark,
        child: LayoutBuilder(builder: (context, constraints) {
          final width =
              math.min(widget.assigned ? 40.0 : 260.0, constraints.maxWidth);
          final limit = math.max(0.0, (constraints.maxWidth - width) / 2);
          final dx = offset.clamp(-limit, limit).toDouble();
          Widget handle = widget.assigned
              ? SizedBox(
                  width: width,
                  height: 16,
                  child: InkWell(
                      onTap: widget.onExpand,
                      child: const Icon(Icons.keyboard_arrow_down, size: 16)))
              : SizedBox(
                  width: width,
                  height: 30,
                  child: Row(children: [
                    Expanded(
                        child: TextButton(
                            onPressed: widget.onChoose,
                            style: TextButton.styleFrom(
                                foregroundColor: rdgenToolbarAccent(context),
                                padding:
                                    const EdgeInsets.symmetric(horizontal: 8)),
                            child: RdgenOrganizationPulse(
                                child: Text(translate('Assign organization'),
                                    maxLines: 1, softWrap: false)))),
                    IconButton(
                        onPressed: widget.onExpand,
                        icon: const Icon(Icons.keyboard_arrow_down, size: 18),
                        tooltip: translate('Expand toolbar'),
                        constraints: const BoxConstraints.tightFor(
                            width: 28, height: 28),
                        padding: EdgeInsets.zero),
                  ]));
          handle = GestureDetector(
              onPanUpdate: (details) {
                setState(() {
                  offset =
                      (dx + details.delta.dx).clamp(-limit, limit).toDouble();
                });
              },
              child: Material(
                  color: widget.assigned
                      ? rdgenToolbarSurface(context)
                      : rdgenToolbarAccent(context).withOpacity(.16),
                  borderRadius:
                      const BorderRadius.vertical(bottom: Radius.circular(6)),
                  child: handle));
          return Align(
              alignment: Alignment.topCenter,
              child: widget.collapsed
                  ? Transform.translate(offset: Offset(dx, 0), child: handle)
                  : ConstrainedBox(
                      constraints:
                          BoxConstraints(maxWidth: constraints.maxWidth),
                      child: Material(
                          color: rdgenToolbarSurface(context),
                          elevation: 4,
                          borderRadius: const BorderRadius.vertical(
                              bottom: Radius.circular(8)),
                          child:
                              RdgenCompactToolbarScope(child: widget.child))));
        }));
  }
}

class RdgenOrganizationToolbarButton extends StatelessWidget {
  final String? name;
  final VoidCallback? onPressed;
  final int additionalCount;
  const RdgenOrganizationToolbarButton(
      {super.key,
      this.name,
      this.additionalCount = 0,
      required this.onPressed});
  @override
  Widget build(BuildContext context) => ConstrainedBox(
      constraints:
          BoxConstraints(maxWidth: name == null ? double.infinity : 280),
      child: TextButton(
          onPressed: onPressed,
          style: rdgenToolbarButtonStyle(
              foreground: rdgenToolbarForeground(context),
              background: rdgenToolbarDark(context) ? const Color(0xff292b2d) : const Color(0xffebeef1),
              border: name == null
                  ? const Color(0xff705932)
                  : const Color(0xff454950)),
          child: Row(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.center,
              children: [
                RdgenToolbarGlyph('organization', color: rdgenToolbarAccent(context)),
                const SizedBox(width: 7),
                Flexible(
                    child: RdgenOrganizationPulse(
                        active: name == null,
                        child: Text(name ?? translate('Assign organization'),
                            maxLines: 1,
                            softWrap: false,
                            overflow: name == null
                                ? TextOverflow.visible
                                : TextOverflow.ellipsis,
                            style: TextStyle(
                                color: name == null
                                    ? rdgenToolbarAccent(context)
                                    : rdgenToolbarForeground(context),
                                fontSize: 14,
                                height: 1,
                                fontWeight: FontWeight.w500)))),
                if (additionalCount > 0)
                  Padding(
                      padding: const EdgeInsets.only(left: 4),
                      child: Text('+$additionalCount',
                          style: const TextStyle(
                              color: Colors.white54, fontSize: 11))),
                const SizedBox(width: 7),
                SizedBox(width: 14, height: 14,
                    child: RdgenToolbarGlyph('down', color: rdgenToolbarAccent(context))),
              ])));
}

ButtonStyle rdgenToolbarButtonStyle(
        {Color foreground = Colors.white, Color background = Colors.transparent,
        Color border = Colors.transparent}) =>
    TextButton.styleFrom(
        foregroundColor: foreground,
        backgroundColor: background,
        minimumSize: const Size(32, 30),
        maximumSize: const Size(double.infinity, 30),
        padding: const EdgeInsets.symmetric(horizontal: 8),
        visualDensity: VisualDensity.standard,
        tapTargetSize: MaterialTapTargetSize.shrinkWrap,
        shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(4),
            side: BorderSide(color: border)));

class RdgenDisplayCounter extends StatelessWidget {
  final int current;
  final int total;
  const RdgenDisplayCounter(
      {super.key, required this.current, required this.total});
  @override
  Widget build(BuildContext context) => total <= 1
      ? const SizedBox.shrink()
      : SizedBox(
          width: 78,
          height: 30,
          child: Row(
              mainAxisAlignment: MainAxisAlignment.center,
              crossAxisAlignment: CrossAxisAlignment.center,
              children: [
                const RdgenToolbarGlyph('monitor'),
                const SizedBox(width: 7),
                Text('${current < 0 ? "*" : current + 1}/$total',
                    style: TextStyle(
                        color: rdgenToolbarForeground(context), fontSize: 14, height: 1)),
                const SizedBox(width: 5),
                const SizedBox(
                    width: 14, height: 14, child: RdgenToolbarGlyph('down')),
              ]));
}

class RdgenOrganizationPulse extends StatefulWidget {
  final Widget child;
  final bool active;
  const RdgenOrganizationPulse(
      {super.key, required this.child, this.active = true});
  @override
  State<RdgenOrganizationPulse> createState() => _RdgenOrganizationPulseState();
}

class _RdgenOrganizationPulseState extends State<RdgenOrganizationPulse>
    with SingleTickerProviderStateMixin {
  late final AnimationController controller = AnimationController(
      vsync: this, duration: const Duration(milliseconds: 900));
  late final Animation<double> opacity = Tween<double>(begin: 1, end: .25)
      .animate(CurvedAnimation(parent: controller, curve: Curves.easeInOut));
  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    sync();
  }

  @override
  void didUpdateWidget(RdgenOrganizationPulse oldWidget) {
    super.didUpdateWidget(oldWidget);
    sync();
  }

  void sync() {
    if (widget.active &&
        !MediaQuery.disableAnimationsOf(context) &&
        TickerMode.of(context)) {
      if (!controller.isAnimating) controller.repeat(reverse: true);
    } else {
      controller.stop();
      controller.value = 0;
    }
  }

  @override
  void dispose() {
    controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => RepaintBoundary(
      child: FadeTransition(opacity: opacity, child: widget.child));
}

/// Small stroke icons share a 24px canvas and a consistent 1.5px line.
class RdgenToolbarGlyph extends StatelessWidget {
  final String kind;
  final Color? color;
  const RdgenToolbarGlyph(this.kind, {super.key, this.color});
  @override
  Widget build(BuildContext context) => SizedBox(
      width: 22,
      height: 22,
      child: CustomPaint(painter: _ToolbarGlyphPainter(kind, color ?? rdgenToolbarForeground(context))));
}

class _ToolbarGlyphPainter extends CustomPainter {
  final String kind;
  final Color color;
  _ToolbarGlyphPainter(this.kind, this.color);
  @override
  void paint(Canvas canvas, Size size) {
    canvas.scale(size.width / 24, size.height / 24);
    final paint = Paint()
      ..color = color
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1.5
      ..strokeCap = StrokeCap.round
      ..strokeJoin = StrokeJoin.round;
    void line(double x, double y, double a, double b) =>
        canvas.drawLine(Offset(x, y), Offset(a, b), paint);
    void rect(double x, double y, double w, double h) => canvas.drawRRect(
        RRect.fromRectAndRadius(
            Rect.fromLTWH(x, y, w, h), const Radius.circular(1)),
        paint);
    switch (kind) {
      case 'monitor':
        rect(3, 4, 18, 12);
        line(12, 16, 12, 20);
        line(8, 20, 16, 20);
        break;
      case 'organization':
        rect(4, 7, 6, 14);
        rect(10, 3, 6, 18);
        rect(16, 10, 4, 11);
        line(2, 21, 22, 21);
        for (final x in [6.0, 12.0, 18.0]) {
          for (final y in [11.0, 15.0, 18.0]) {
            line(x, y, x + .5, y);
          }
        }
        line(12, 6, 14, 6);
        break;
      case 'pin':
        canvas.save();
        canvas.translate(12, 11);
        canvas.rotate(.65);
        line(-4, -7, 4, -7);
        line(-3, -7, -3, 0);
        line(3, -7, 3, 0);
        line(-3, 0, -6, 4);
        line(3, 0, 6, 4);
        line(-6, 4, 6, 4);
        line(0, 4, 0, 11);
        canvas.restore();
        break;
      case 'fullscreen':
        for (final x in [4.0, 20.0]) {
          for (final y in [4.0, 20.0]) {
            line(x, y, x + (x == 4 ? 5 : -5), y);
            line(x, y, x, y + (y == 4 ? 5 : -5));
          }
        }
        break;
      case 'settings':
        for (final y in [5.0, 12.0, 19.0]) {
          final x = y == 12 ? 15.0 : 8.0;
          line(3, y, x - 2, y);
          line(x + 2, y, 21, y);
          canvas.drawCircle(Offset(x, y), 2, paint);
        }
        break;
      case 'keyboard':
        rect(2, 5, 20, 14);
        for (final y in [9.0, 12.0]) {
          for (final x in [6.0, 10.0, 14.0, 18.0]) {
            line(x, y, x + .5, y);
          }
        }
        line(7, 16, 17, 16);
        break;
      case 'bolt':
        canvas.drawPath(
            Path()
              ..moveTo(14, 2)
              ..lineTo(5, 14)
              ..lineTo(11, 14)
              ..lineTo(10, 22)
              ..lineTo(20, 9)
              ..lineTo(13, 9)
              ..close(),
            paint);
        break;
      case 'more':
        for (final x in [5.0, 12.0, 19.0]) {
          canvas.drawCircle(Offset(x, 12), 1, paint);
        }
        break;
      case 'up':
        line(7, 14, 12, 9);
        line(12, 9, 17, 14);
        break;
      case 'down':
        line(7, 10, 12, 15);
        line(12, 15, 17, 10);
        break;
      case 'close':
        line(6, 6, 18, 18);
        line(18, 6, 6, 18);
        break;
    }
  }

  @override
  bool shouldRepaint(_ToolbarGlyphPainter oldDelegate) =>
      kind != oldDelegate.kind || color != oldDelegate.color;
}
