import 'dart:math' as math;
import 'dart:ui';
import 'package:flutter/foundation.dart';
import 'package:flutter/rendering.dart' show CustomPainter;

class SnowLedge {
  final double x, y, limit;
  final int band;
  double depth;
  SnowLedge(this.x, this.y, this.limit, this.depth, {this.band = 0});
}

class SnowParticle {
  double x, y, vx, vy, age = 0;
  final double radius;
  final bool debris;
  SnowParticle(this.x, this.y, this.vx, this.vy, this.radius, this.debris);
}

/// Fixed-size pools; collision queries touch only one 2px column per particle.
class SnowField extends ChangeNotifier {
  static const step = 2.0;
  static const fallingCount = 66;
  static const maxDebris = 110;
  final math.Random _random = math.Random(24);
  final List<SnowParticle> particles = [];
  List<List<SnowLedge>> columns = [];
  final List<List<SnowLedge>> capGroups = [];
  List<double> floor = [], floorTarget = [];
  List<Rect> protectedAreas = [];
  Size size = Size.zero;
  double _phase = 0;
  bool enabled = true;
  int lastStepMicros = 0;
  final Stopwatch _watch = Stopwatch();

  bool get ready => size.width > 0 && columns.isNotEmpty;
  int get debrisCount => particles.where((p) => p.debris).length;
  bool canSweep(Offset p) =>
      p.dx >= 0 &&
      p.dx < size.width &&
      p.dy >= 0 &&
      p.dy < size.height &&
      !protectedAreas.any((r) => r.contains(p));

  void configure(Size next, List<List<SnowLedge>> ledges, List<Rect> blocked) {
    size = next;
    columns = ledges;
    capGroups.clear();
    for (var band = 0; band < 7; band++) {
      var group = <SnowLedge>[];
      for (final column in columns) {
        final matches = column.where((ledge) => ledge.band == band);
        final ledge = matches.isEmpty ? null : matches.first;
        if (ledge == null ||
            group.isNotEmpty && (ledge.y - group.last.y).abs() > 4) {
          if (group.isNotEmpty) capGroups.add(group);
          group = [];
        }
        if (ledge != null) group.add(ledge);
      }
      if (group.isNotEmpty) capGroups.add(group);
    }
    protectedAreas = blocked;
    floorTarget = List.generate((next.width / step).ceil(), (i) {
      final x = i * step;
      final u = x / next.width;
      return 15 +
          8 * math.sin(u * 7 + 0.8) +
          4 * math.sin(u * 21 + 1.1) +
          18 * math.pow((2 * u - 1).abs(), 3) +
          1.3 * math.sin(u * 97);
    });
    reset();
  }

  void reset() {
    floor = List.of(floorTarget);
    for (final column in columns) {
      for (final ledge in column) {
        ledge.depth = ledge.limit *
            (0.45 + 0.18 * math.sin(ledge.x * 0.085 + ledge.y * 0.07));
      }
    }
    particles.clear();
    if (size.height > 0) {
      for (var i = 0; i < fallingCount; i++) {
        particles.add(_newFlake(randomHeight: true));
      }
    }
    notifyListeners();
  }

  SnowParticle _newFlake({bool randomHeight = false}) => SnowParticle(
      _random.nextDouble() * size.width,
      randomHeight
          ? _random.nextDouble() * size.height
          : -8 - _random.nextDouble() * 30,
      -4 + _random.nextDouble() * 8,
      15 + _random.nextDouble() * 24,
      0.7 + _random.nextDouble() * 1.25,
      false);

  void _recycle(SnowParticle p) {
    final next = _newFlake();
    p.x = next.x;
    p.y = next.y;
    p.vx = next.vx;
    p.vy = next.vy;
    p.age = 0;
  }

  void _fragment(double x, double y, double vx, double vy, int amount) {
    var available = maxDebris - debrisCount;
    for (var i = 0; i < amount && available > 0; i++, available--) {
      particles.add(SnowParticle(
          x + _random.nextDouble() * 8 - 4,
          y,
          vx + _random.nextDouble() * 28 - 14,
          vy - _random.nextDouble() * 22,
          1 + _random.nextDouble() * 1.6,
          true));
    }
  }

  void tick(double dt) {
    if (!enabled || !ready) return;
    _watch
      ..reset()
      ..start();
    dt = dt.clamp(0.0, 0.05);
    _phase += dt;
    // Refill swipe depressions only up to the immutable target, never add deposits.
    for (var i = 0; i < floor.length; i++) {
      floor[i] = math.min(floorTarget[i], floor[i] + dt * 1.5);
    }
    final count = particles.length;
    for (var i = count - 1; i >= 0; i--) {
      final p = particles[i];
      final previousY = p.y;
      p.age += dt;
      if (p.debris) {
        p.vy += 100 * dt;
        p.vx *= math.exp(-0.7 * dt);
      } else {
        p.vy += (22 + p.radius * 6 - p.vy) * dt * 0.8;
        p.vx *= math.exp(-dt * 0.2);
      }
      p.x += (p.vx + (p.debris ? 0 : math.sin(_phase * 0.7 + i) * 6)) * dt;
      p.y += p.vy * dt;
      if (p.x < -10 ||
          p.x > size.width + 10 ||
          p.y > size.height + 8 ||
          (p.debris && p.age > 5)) {
        if (p.debris) {
          particles.removeAt(i);
        } else {
          _recycle(p);
        }
        continue;
      }
      final bin = (p.x / step).floor().clamp(0, columns.length - 1);
      var landed = false;
      if (p.vy > 0 && (!p.debris || p.age > 0.35)) {
        for (final ledge in columns[bin]) {
          final top = ledge.y - ledge.depth;
          if (previousY + p.radius <= top && p.y + p.radius >= top) {
            ledge.depth += p.debris ? 0.65 : 0.8;
            if (ledge.depth > ledge.limit) {
              ledge.depth *= 0.5;
              _fragment(ledge.x, top - 2, _random.nextDouble() * 35 - 17, 8, 3);
            }
            landed = true;
            break;
          }
        }
      }
      final floorBin = bin.clamp(0, floor.length - 1);
      if (landed || p.y + p.radius >= size.height - floor[floorBin]) {
        if (p.debris) {
          particles.removeAt(i);
        } else {
          _recycle(p);
        }
      }
    }
    _watch.stop();
    lastStepMicros = _watch.elapsedMicroseconds;
    notifyListeners();
  }

  void sweep(Offset from, Offset to, double seconds) {
    if (!ready || !canSweep(from) || !canSweep(to)) return;
    final delta = to - from;
    if (delta.distance < 0.7) return;
    final velocity = delta / math.max(seconds, 0.008);
    final speed = velocity.distance.clamp(0.0, 1000.0);
    final radius = 20.0 + speed * 0.009;
    double distance(Offset p) {
      final length2 = delta.distanceSquared;
      final t = length2 == 0
          ? 0.0
          : ((p - from).dx * delta.dx + (p - from).dy * delta.dy) / length2;
      return (p - (from + delta * t.clamp(0.0, 1.0))).distance;
    }

    final vx = velocity.dx.clamp(-300.0, 300.0) * 0.55;
    var launched = 0;
    for (final p in particles) {
      if (distance(Offset(p.x, p.y)) < radius) {
        p.vx = vx;
        p.vy = velocity.dy.clamp(-180.0, 180.0) * 0.4 - 25;
      }
    }
    final first = ((math.min(from.dx, to.dx) - radius) / step)
        .floor()
        .clamp(0, columns.length - 1);
    final last = ((math.max(from.dx, to.dx) + radius) / step)
        .ceil()
        .clamp(0, columns.length - 1);
    for (var i = first; i <= last; i++) {
      for (final ledge in columns[i]) {
        final point = Offset(ledge.x, ledge.y - ledge.depth * 0.5);
        if (!canSweep(point) || distance(point) > radius || ledge.depth < 0.3) {
          continue;
        }
        if (launched < 24 && i % 3 == 0) {
          _fragment(
              ledge.x, ledge.y - ledge.depth - 2, vx, -30 - speed * 0.08, 2);
          launched += 2;
        }
        ledge.depth *= 0.12;
      }
      final x = i * step;
      final floorPoint = Offset(x, size.height - floor[i] * 0.55);
      if (distance(floorPoint) <= radius + 5) {
        if (launched < 32 && i % 4 == 0 && floor[i] > 2) {
          _fragment(x, size.height - floor[i] - 2, vx, -45 - speed * 0.1, 2);
          launched += 2;
        }
        floor[i] = math.max(1.0, floor[i] - 13);
      }
    }
    notifyListeners();
  }
}

class SnowPainter extends CustomPainter {
  final SnowField field;
  final bool dark;
  SnowPainter(this.field, this.dark) : super(repaint: field);
  @override
  void paint(Canvas canvas, Size size) {
    if (!field.ready) return;
    canvas.save();
    canvas.clipRect(Offset.zero & size);
    final powder = Paint()
      ..color = dark ? const Color(0xfff1f6fc) : const Color(0xffe2ebf4);
    final shadow = Paint()..color = const Color(0xff8fa4ba).withOpacity(0.22);
    for (final group in field.capGroups) {
      if (!group.any((ledge) => ledge.depth > 0.2)) continue;
      final first = group.first;
      final last = group.last;
      final cap = Path()
        ..moveTo(first.x - 1, first.y)
        ..quadraticBezierTo(
            first.x - 1, first.y - first.depth, first.x, first.y - first.depth);
      for (final ledge in group.skip(1)) {
        cap.lineTo(ledge.x, ledge.y - ledge.depth);
      }
      cap.quadraticBezierTo(
          last.x + 1, last.y - last.depth, last.x + 1, last.y);
      for (final ledge in group.reversed) {
        cap.lineTo(ledge.x, ledge.y);
      }
      cap.close();
      canvas.drawPath(cap.shift(const Offset(0, 0.4)), shadow);
      canvas.drawPath(cap, powder);
    }
    for (final p in field.particles) {
      if (field.protectedAreas.any((r) => r.contains(Offset(p.x, p.y)))) {
        continue;
      }
      final opacity =
          p.debris ? (1 - p.age / 5).clamp(0.0, 0.95) : 0.55 + p.radius * 0.15;
      powder.color = (dark ? const Color(0xfff2f6ff) : const Color(0xffb6c9dc))
          .withOpacity(opacity);
      canvas.drawCircle(Offset(p.x, p.y), p.radius, powder);
    }
    final path = Path()..moveTo(0, size.height);
    for (var i = 0; i < field.floor.length; i++) {
      path.lineTo(i * SnowField.step, size.height - field.floor[i]);
    }
    path
      ..lineTo(size.width, size.height - field.floor.last)
      ..lineTo(size.width, size.height)
      ..close();
    final snow = Paint()
      ..shader = Gradient.linear(
          Offset(0, size.height - 45),
          Offset(0, size.height),
          dark
              ? [const Color(0xfff9fcff), const Color(0xffbecddd)]
              : [const Color(0xfff8fbff), const Color(0xffc0d0df)]);
    canvas.drawPath(path, snow);
    canvas.restore();
  }

  @override
  bool shouldRepaint(SnowPainter oldDelegate) =>
      oldDelegate.dark != dark || oldDelegate.field != field;
}
