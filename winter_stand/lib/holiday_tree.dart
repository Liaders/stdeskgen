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
  Offset project(double px, double height, double depth) => Offset(
      x + px * 0.82 - depth * 0.57,
      ground - height * 0.94 + (px * 0.57 + depth * 0.82) * 0.45);
  for (var tier = 5; tier >= 0; tier--) {
    final height = 190.0 - tier * 24, radius = 13.0 + tier * 8.0;
    final angles = List.generate(7, (i) => i * math.pi * 2 / 7 + tier * 0.29);
    angles.sort((a, b) => (math.cos(a) * 0.57 + math.sin(a) * 0.82)
        .compareTo(math.cos(b) * 0.57 + math.sin(b) * 0.82));
    for (var j = 0; j < angles.length; j++) {
      final angle = angles[j], dx = math.cos(angle), dz = math.sin(angle);
      final reach = radius * (0.92 + 0.10 * math.sin(tier * 2 + j));
      final root = project(dx * 2, height, dz * 2);
      final tip = project(dx * reach, height - 28, dz * reach);
      final left = project(dx * reach * 0.55 - dz * reach * 0.64, height - 15,
          dz * reach * 0.55 + dx * reach * 0.64);
      final right = project(dx * reach * 0.55 + dz * reach * 0.64, height - 17,
          dz * reach * 0.55 - dx * reach * 0.64);
      final branch = Path()
        ..moveTo(root.dx, root.dy)
        ..quadraticBezierTo(left.dx, left.dy, tip.dx, tip.dy)
        ..quadraticBezierTo(right.dx, right.dy, root.dx, root.dy)
        ..close();
      c.save();
      c.translate(0, 3.2);
      c.drawPath(branch, Paint()..color = const Color(0xff103e30));
      c.restore();
      c.drawPath(
          branch,
          Paint()
            ..shader = ui.Gradient.linear(left, right, [
              const Color(0xff51a17b),
              const Color(0xff267555),
              const Color(0xff134b38)
            ], [
              0,
              0.5,
              1
            ]));
      c.drawPath(
          Path()
            ..moveTo(root.dx * 0.35 + left.dx * 0.65,
                root.dy * 0.35 + left.dy * 0.65)
            ..quadraticBezierTo(
                left.dx, left.dy - 1, tip.dx - 0.5, tip.dy - 0.6),
          Paint()
            ..color = const Color(0xffedf8f5)
            ..strokeWidth = 1.4
            ..style = PaintingStyle.stroke
            ..strokeCap = StrokeCap.round);
      final ridge = Offset.lerp(root, tip, 0.72)!;
      if (j % 2 == 0) {
        final color = (tier + j) % 3 == 0
            ? const Color(0xffd55042)
            : const Color(0xffe8bd62);
        c.drawLine(
            ridge,
            ridge + const Offset(0, 4),
            Paint()
              ..color = const Color(0xffb39e63)
              ..strokeWidth = 0.7);
        c.drawCircle(ridge + const Offset(0.6, 5), 3.1,
            Paint()..color = const Color(0x5510241d));
        c.drawCircle(
            ridge + const Offset(0, 4),
            2.7,
            Paint()
              ..shader = ui.Gradient.radial(
                  ridge + const Offset(-1, 3),
                  4,
                  [Color.lerp(color, const Color(0xffffffff), 0.5)!, color],
                  [0, 1]));
      }
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
        top = ground - 11 - (i % 2) * 11 - i * 1.5,
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
          ..lineTo(left + 31 + i * 1.5, top - 8 - i * 1.5)
          ..lineTo(left + 31 + i * 1.5, top + height - 5)
          ..lineTo(left + 25, top + height)
          ..close(),
        Paint()..color = Color.lerp(color, const Color(0xff152d37), 0.3)!);
    c.drawPath(
        Path()
          ..moveTo(left, top)
          ..lineTo(left + 7, top - 8 - i * 1.5)
          ..lineTo(left + 31 + i * 1.5, top - 8 - i * 1.5)
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
          ..lineTo(left + 19, top - 8 - i * 1.5),
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
