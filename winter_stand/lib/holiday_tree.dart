import 'dart:math' as math;
import 'dart:ui' as ui;
import 'package:flutter/painting.dart';

/// Static illustration: bowed tiers, contact shadows and perspective gift boxes.
void paintHolidayTree(Canvas c, Size size) {
  final x = size.width - 57, ground = size.height - 18;
  final snow = Path()
    ..moveTo(0, size.height)
    ..lineTo(0, size.height - 14)
    ..cubicTo(35, size.height - 29, 65, size.height - 13, 94, size.height - 20)
    ..cubicTo(135, size.height - 36, 170, size.height - 31, size.width,
        size.height - 16)
    ..lineTo(size.width, size.height)
    ..close();
  c.drawPath(
      snow,
      Paint()
        ..shader = ui.Gradient.linear(
            Offset(0, size.height - 36),
            Offset(0, size.height),
            [const Color(0xfff7fbff), const Color(0xffc4d3e1)]));
  c.drawOval(
      Rect.fromCenter(
          center: Offset(x + 5, ground + 1), width: 108, height: 17),
      Paint()
        ..shader = ui.Gradient.radial(Offset(x + 5, ground + 1), 55,
            [const Color(0x55546775), const Color(0x00546775)]));
  c.drawRRect(
      RRect.fromRectAndRadius(
          Rect.fromLTWH(x - 5, ground - 58, 10, 58), const Radius.circular(3)),
      Paint()
        ..shader = ui.Gradient.linear(Offset(x - 5, 0), Offset(x + 5, 0),
            [const Color(0xff9b744d), const Color(0xff483326)]));
  for (var tier = 5; tier >= 0; tier--) {
    final y = ground - 158 + tier * 23, half = 12 + tier * 6.9;
    final left = x - half, right = x + half;
    final body = Path()
      ..moveTo(x - 2, y - 24)
      ..cubicTo(x - half * 0.38, y - 8, left + 8, y + 7, left, y + 13)
      ..cubicTo(left + half * 0.40, y + 29, right - half * 0.38, y + 33, right,
          y + 12)
      ..cubicTo(right - 10, y + 7, x + half * 0.36, y - 9, x - 2, y - 24)
      ..close();
    c.drawPath(
        body,
        Paint()
          ..shader =
              ui.Gradient.linear(Offset(left, y), Offset(right, y + 17), [
            const Color(0xff175642),
            const Color(0xff3e9672),
            const Color(0xff1d7152),
            const Color(0xff0b3d30)
          ], [
            0,
            0.35,
            0.68,
            1
          ]));
    final underside = Path()
      ..moveTo(left, y + 13)
      ..cubicTo(x - half * 0.45, y + 22, x + half * 0.50, y + 29, right, y + 12)
      ..cubicTo(x + half * 0.45, y + 35, x - half * 0.45, y + 30, left, y + 13)
      ..close();
    c.drawPath(underside, Paint()..color = const Color(0xff103f32));
    final ridge = Path()
      ..moveTo(left + 2, y + 12)
      ..cubicTo(
          x - half * 0.60, y + 15, x + half * 0.25, y + 28, right - 3, y + 12);
    c.drawPath(
        ridge,
        Paint()
          ..color = const Color(0xffe6f3f3)
          ..style = PaintingStyle.stroke
          ..strokeWidth = 2.7
          ..strokeCap = StrokeCap.round);
    final garland = Path()
      ..moveTo(left + half * 0.30, y + 4)
      ..cubicTo(x - half * 0.3, y + 14, x + half * 0.2, y + 20,
          right - half * 0.20, y + 7);
    c.drawPath(
        garland,
        Paint()
          ..color = const Color(0xffd9bc6a)
          ..style = PaintingStyle.stroke
          ..strokeWidth = 0.9);
    for (var j = 0; j < 3; j++) {
      final ox = x + (j - 1.1) * half * 0.55, oy = y + 8 + j * 2.5;
      final color = [
        const Color(0xffd44e43),
        const Color(0xffefc76a),
        const Color(0xff69a5b3)
      ][(tier + j) % 3];
      c.drawCircle(Offset(ox + 1, oy + 1), 3.6,
          Paint()..color = const Color(0x55102620));
      c.drawCircle(
          Offset(ox, oy),
          3.2,
          Paint()
            ..shader = ui.Gradient.radial(Offset(ox - 1, oy - 1), 5, [
              Color.lerp(color, const Color(0xffffffff), 0.4)!,
              color,
              const Color(0xff543a2b)
            ], [
              0,
              0.55,
              1
            ]));
      c.drawCircle(Offset(ox - 1, oy - 1), 0.9,
          Paint()..color = const Color(0xfffff7de));
    }
  }
  final center = Offset(x, size.height - 206), star = Path();
  for (var i = 0; i < 10; i++) {
    final a = -math.pi / 2 + i * math.pi / 5, r = i.isEven ? 8.5 : 3.7;
    final p = center + Offset(math.cos(a) * r, math.sin(a) * r);
    if (i == 0) {
      star.moveTo(p.dx, p.dy);
    } else {
      star.lineTo(p.dx, p.dy);
    }
  }
  c.drawPath(
      star..close(),
      Paint()
        ..shader = ui.Gradient.linear(
            center - const Offset(5, 7), center + const Offset(6, 7), [
          const Color(0xfffff0b0),
          const Color(0xffffca55),
          const Color(0xffc68a31)
        ], [
          0,
          0.5,
          1
        ]));
  for (var i = 0; i < 3; i++) {
    final left = x - 50 + i * 31,
        top = ground - 11 - (i % 2) * 11,
        height = 23.0 + (i % 2) * 11;
    final color = [
      const Color(0xffb94449),
      const Color(0xffd9a74c),
      const Color(0xff408796)
    ][i];
    final front = Rect.fromLTWH(left, top, 25, height);
    c.drawOval(Rect.fromLTWH(left - 3, ground + 8, 36, 7),
        Paint()..color = const Color(0x22506375));
    c.drawRect(
        front,
        Paint()
          ..shader = ui.Gradient.linear(front.topLeft, front.bottomRight,
              [Color.lerp(color, const Color(0xffffffff), 0.12)!, color]));
    c.drawPath(
        Path()
          ..moveTo(left + 25, top)
          ..lineTo(left + 32, top - 5)
          ..lineTo(left + 32, top + height - 5)
          ..lineTo(left + 25, top + height)
          ..close(),
        Paint()..color = Color.lerp(color, const Color(0xff152d37), 0.3)!);
    c.drawPath(
        Path()
          ..moveTo(left, top)
          ..lineTo(left + 7, top - 5)
          ..lineTo(left + 32, top - 5)
          ..lineTo(left + 25, top)
          ..close(),
        Paint()..color = Color.lerp(color, const Color(0xffffffff), 0.3)!);
    final ribbon = Paint()
      ..color = const Color(0xfff8d895)
      ..strokeWidth = 3;
    c.drawLine(Offset(left + 12, top), Offset(left + 12, top + height), ribbon);
    c.drawLine(Offset(left, top + 7), Offset(left + 25, top + 7), ribbon);
    c.drawPath(
        Path()
          ..moveTo(left + 12, top)
          ..lineTo(left + 19, top - 5),
        ribbon);
    ribbon
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1.5;
    c.drawOval(
        Rect.fromCenter(center: Offset(left + 8, top - 3), width: 9, height: 5),
        ribbon);
    c.drawOval(
        Rect.fromCenter(
            center: Offset(left + 16, top - 4), width: 8, height: 5),
        ribbon);
  }
  c.drawPath(
      Path()
        ..moveTo(0, size.height)
        ..lineTo(0, size.height - 5)
        ..quadraticBezierTo(45, size.height - 11, 86, size.height - 6)
        ..quadraticBezierTo(145, size.height - 1, size.width, size.height - 9)
        ..lineTo(size.width, size.height)
        ..close(),
      Paint()..color = const Color(0xffe5eff7));
}
