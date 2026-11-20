import 'dart:math' as math;
import 'package:flutter/painting.dart';
import 'snow_field.dart';

/// Cached vector drawing; its branch surfaces use the very same geometry.
class WinterTree {
  final Size size;
  WinterTree(this.size);
  double get center => size.width - 53;
  double get top => size.height - 184;
  double branchWidth(int tier) => 12 + tier * 6.2;
  double branchY(int tier, double x) =>
      top + 24 + tier * 22 + (x - center).abs() * 0.34;

  void addSurfaces(List<List<SnowLedge>> columns) {
    for (var tier = 0; tier < 6; tier++) {
      final half = branchWidth(tier);
      for (var bin = 0; bin < columns.length; bin++) {
        final x = bin * SnowField.step;
        if ((x - center).abs() <= half) {
          columns[bin]
              .add(SnowLedge(x, branchY(tier, x), 3.2, 0, band: 10 + tier));
        }
      }
    }
  }

  void paint(Canvas canvas, bool dark) {
    final trunkBottom = size.height - 7;
    canvas.drawRRect(
        RRect.fromRectAndRadius(
            Rect.fromLTRB(center - 4, top + 112, center + 4, trunkBottom),
            const Radius.circular(2)),
        Paint()..color = const Color(0xff76533a));
    canvas.drawPath(
        Path()
          ..moveTo(center, top + 24)
          ..lineTo(center - 23, top + 152)
          ..lineTo(center + 23, top + 152)
          ..close(),
        Paint()..color = const Color(0xff1a604c));
    for (var tier = 5; tier >= 0; tier--) {
      final half = branchWidth(tier);
      final y = branchY(tier, center);
      final branch = Path()
        ..moveTo(center, y)
        ..lineTo(center - half, branchY(tier, center - half))
        ..quadraticBezierTo(center - half + 10, y + 19, center - 3, y + 15)
        ..lineTo(center + 3, y + 15)
        ..quadraticBezierTo(center + half - 10, y + 19, center + half,
            branchY(tier, center + half))
        ..close();
      canvas.drawPath(
          branch,
          Paint()
            ..color = tier.isEven
                ? const Color(0xff24745b)
                : const Color(0xff1a604c));
      canvas.drawLine(
          Offset(center - half + 3, branchY(tier, center - half) + 1),
          Offset(center, y + 1),
          Paint()
            ..color = const Color(0xff459675)
            ..strokeWidth = 1);
    }
    final star = Path();
    final starCenter = Offset(center, top + 17);
    for (var i = 0; i < 10; i++) {
      final radius = i.isEven ? 7.0 : 3.1;
      final a = -math.pi / 2 + i * math.pi / 5;
      final p = starCenter + Offset(math.cos(a), math.sin(a)) * radius;
      if (i == 0) {
        star.moveTo(p.dx, p.dy);
      } else {
        star.lineTo(p.dx, p.dy);
      }
    }
    canvas.drawPath(star..close(), Paint()..color = const Color(0xffedb654));
    for (final ornament in [
      (1, -0.5, 0xffef7f1a),
      (2, 0.6, 0xffd65758),
      (3, -0.45, 0xffe8bf65),
      (4, 0.55, 0xffe16059),
      (5, -0.6, 0xffedb654)
    ]) {
      final x = center + branchWidth(ornament.$1) * ornament.$2;
      final y = branchY(ornament.$1, x) + 8;
      canvas.drawCircle(Offset(x, y), 2.4, Paint()..color = Color(ornament.$3));
    }
  }
}
