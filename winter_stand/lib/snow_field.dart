import 'dart:math' as math;
import 'dart:ui';
import 'package:flutter/foundation.dart';
import 'package:flutter/rendering.dart' show CustomPainter;

class SnowLedge {
  final double x, y, limit;
  final int band;
  double depth;
  List<SnowLedge>? group;
  int groupIndex = 0;
  SnowLedge(this.x, this.y, this.limit, this.depth, {this.band = 0});
}

class SnowParticle {
  double x, y, vx, vy, age = 0, energy = 0;
  double previousX, previousY, radius, phase;
  final bool debris;
  SnowParticle(this.x, this.y, this.vx, this.vy, this.radius, this.debris,
      {this.phase = 0})
      : previousX = x,
        previousY = y;
}

class SnowTileFlake {
  final double x, y, radius;
  final int layer;
  SnowTileFlake(this.x, this.y, this.radius, this.layer);
}

/// Fixed physics at 30Hz, interpolated presentation at the selected frame limit.
/// Buffers and debris objects are reused; the static letter paths are cached.
class SnowField extends ChangeNotifier {
  final settled = ChangeNotifier();
  double _settledElapsed = 0;
  bool _floorWasMoving = false;

  void _notifyFrame(double seconds, {bool immediate = false}) {
    _settledElapsed += seconds;
    if (immediate ||
        floorMoving ||
        _floorWasMoving ||
        (_capsDirty && _settledElapsed >= 0.15)) {
      settled.notifyListeners();
      _settledElapsed = 0;
    }
    _floorWasMoving = floorMoving;
    notifyListeners();
  }

  @override
  void dispose() {
    settled.dispose();
    super.dispose();
  }

  static const step = 2.0, physicsStep = 1 / 30, floorMaxHeight = 42.0;
  static const fallingCount = 66, maxDebris = 80;
  final math.Random _random = math.Random(24);
  bool lightweight = false;
  double textureTime = 0, _ambientTime = 0, _holeTime = 0;
  Rect? tileHole;
  final Set<SnowTileFlake> _liftedFlakes = {};
  late final List<SnowTileFlake> tileFlakes = (() {
    final random = math.Random(71);
    return List.generate(
        fallingCount,
        (i) => SnowTileFlake(random.nextDouble(), random.nextDouble(),
            0.7 + random.nextDouble() * 1.25, i % 3));
  })();
  static const tileSpeeds = [18.0, 26.0, 34.0];
  double tileSway(int layer) => math.sin(textureTime * 0.35 + layer * 2) * 5;
  Offset tilePosition(SnowTileFlake flake) => Offset(
      flake.x * size.width + tileSway(flake.layer),
      (flake.y * size.height + textureTime * tileSpeeds[flake.layer]) %
          size.height);
  final List<SnowParticle> particles = [], _spare = [];
  List<List<SnowLedge>> columns = [];
  final List<List<SnowLedge>> capGroups = [];
  final List<Path> _capPaths = [];
  bool _capsDirty = true, _floorMoving = false;
  bool get floorMoving => _floorMoving;
  List<double> floor = [], floorTarget = [], previousFloor = [];
  double floorOffset = 0, _floorSpeed = 0;
  bool get floorVisible => floorOffset.abs() < size.width;
  double floorHeightAt(double x) {
    final local = x - floorOffset;
    if (local < 0 || local >= size.width || floor.isEmpty) return 0;
    return floor[(local / step).floor().clamp(0, floor.length - 1)];
  }

  List<Rect> protectedAreas = [];
  Size size = Size.zero;
  double _phase = 0, _accumulator = 0, renderAlpha = 1;
  bool enabled = true;
  int lastStepMicros = 0, physicsSteps = 0, renderedFrames = 0;
  int particlePaints = 0, settledPaints = 0;
  final Stopwatch _watch = Stopwatch();
  SnowField() {
    for (var i = 0; i < maxDebris; i++) {
      _spare.add(SnowParticle(0, 0, 0, 0, 1, true,
          phase: _random.nextDouble() * math.pi * 2));
    }
  }

  bool get ready => size.width > 0 && columns.isNotEmpty;
  int get debrisCount => maxDebris - _spare.length;
  bool canSweep(Offset p) =>
      (Offset.zero & size).contains(p) &&
      !protectedAreas.any((r) => r.contains(p));

  void configure(Size next, List<List<SnowLedge>> ledges, List<Rect> blocked) {
    size = next;
    columns = ledges;
    protectedAreas = blocked;
    capGroups.clear();
    var maxBand = 0;
    for (final column in columns) {
      column.sort((a, b) => a.y.compareTo(b.y));
      for (final ledge in column) {
        maxBand = math.max(maxBand, ledge.band);
      }
    }
    for (var band = 0; band <= maxBand; band++) {
      var group = <SnowLedge>[];
      for (final column in columns) {
        SnowLedge? ledge;
        for (final entry in column) {
          if (entry.band == band) {
            ledge = entry;
            break;
          }
        }
        if (ledge == null ||
            group.isNotEmpty && (ledge.y - group.last.y).abs() > 3) {
          if (group.isNotEmpty) capGroups.add(group);
          group = [];
        }
        if (ledge != null) group.add(ledge);
      }
      if (group.isNotEmpty) capGroups.add(group);
    }
    for (final group in capGroups) {
      for (var i = 0; i < group.length; i++) {
        group[i].group = group;
        group[i].groupIndex = i;
      }
    }
    floorTarget = List.generate((next.width / step).ceil(), (i) {
      final u = i * step / next.width;
      final edge = (math.min(i, (next.width / step).ceil() - 1 - i) * step / 18)
          .clamp(0.0, 1.0);
      return (17 +
                  6 * math.sin(u * 7 + 0.8) +
                  4 * math.sin(u * 21 + 1.1) +
                  14 * math.pow((2 * u - 1).abs(), 3) +
                  0.7 * math.sin(u * 67))
              .clamp(4.0, floorMaxHeight) *
          edge *
          edge *
          (3 - 2 * edge);
    });
    previousFloor = List.filled(floorTarget.length, 0);
    reset();
  }

  void reset() {
    for (final p in particles) {
      if (p.debris) _spare.add(p);
    }
    particles.clear();
    floor = List.of(floorTarget);
    _floorMoving = false;
    floorOffset = 0;
    _floorSpeed = 0;
    for (var i = 0; i < floor.length; i++) {
      previousFloor[i] = floor[i];
    }
    for (final group in capGroups) {
      for (final ledge in group) {
        ledge.depth = ledge.limit *
            (0.4 + 0.1 * math.sin(ledge.x * 0.08 + ledge.y * 0.04));
      }
    }
    if (size.height > 0) {
      for (var i = 0; i < fallingCount; i++) {
        final p = SnowParticle(0, 0, 0, 0, 1, false);
        _recycle(p, randomHeight: true);
        particles.add(p);
      }
    }
    _accumulator = 0;
    textureTime = 0;
    _ambientTime = 0;
    tileHole = null;
    _liftedFlakes.clear();
    _holeTime = 0;
    renderAlpha = 1;
    _capsDirty = true;
    _notifyFrame(0, immediate: true);
  }

  void _recycle(SnowParticle p, {bool randomHeight = false}) {
    p.x = _random.nextDouble() * size.width;
    p.y = randomHeight
        ? _random.nextDouble() * size.height
        : -8 - _random.nextDouble() * 30;
    p.previousX = p.x;
    p.previousY = p.y;
    p.vx = _random.nextDouble() * 6 - 3;
    p.vy = 17 + _random.nextDouble() * 18;
    p.radius = 0.7 + _random.nextDouble() * 1.25;
    p.phase = _random.nextDouble() * math.pi * 2;
    p.age = 0;
    p.energy = 0;
  }

  void _fragment(double x, double y, double vx, double vy, int amount) {
    for (var i = 0; i < amount && _spare.isNotEmpty; i++) {
      final p = _spare.removeLast();
      p.x = x + _random.nextDouble() * 7 - 3.5;
      p.y = y;
      p.previousX = p.x;
      p.previousY = p.y;
      p.vx = vx + _random.nextDouble() * 65 - 32;
      p.vy = vy - _random.nextDouble() * 35;
      p.radius = 1 + _random.nextDouble() * 1.8;
      p.energy = 30;
      p.age = 0;
      particles.add(p);
    }
  }

  void _retire(int i) {
    final p = particles[i], last = particles.removeLast();
    if (i < particles.length) particles[i] = last;
    _spare.add(p);
  }

  void advance(double seconds) {
    if (!enabled || !ready) return;
    if (lightweight) {
      final dt = seconds.clamp(0.0, 0.1);
      textureTime += dt;
      _ambientTime += dt;
      if (_holeTime > 0) {
        _holeTime -= dt;
        if (_holeTime <= 0) {
          tileHole = null;
          _liftedFlakes.clear();
        }
      }
      if (_ambientTime >= 0.5 && capGroups.isNotEmpty) {
        _ambientTime = 0;
        final group = capGroups[_random.nextInt(capGroups.length)];
        _deposit(group[_random.nextInt(group.length)], 0.18);
      }
    }
    _accumulator += seconds.clamp(0.0, 0.1);
    _watch
      ..reset()
      ..start();
    var steps = 0;
    while (_accumulator >= physicsStep && steps < 3) {
      if (!lightweight || debrisCount > 0 || floorMoving) {
        _simulate(physicsStep);
      }
      _accumulator -= physicsStep;
      steps++;
    }
    _watch.stop();
    if (steps > 0) lastStepMicros = _watch.elapsedMicroseconds;
    renderAlpha = (_accumulator / physicsStep).clamp(0.0, 1.0);
    renderedFrames++;
    _notifyFrame(seconds);
  }

  /// Deterministic simulation entry point for the long-run regression checks.
  void tick(double dt) {
    if (!enabled || !ready) return;
    _simulate(dt.clamp(0.0, 0.05));
    renderAlpha = 1;
    _notifyFrame(0, immediate: true);
  }

  void _deposit(SnowLedge ledge, double amount) {
    final group = ledge.group!;
    const weights = [0.06, 0.12, 0.2, 0.24, 0.2, 0.12, 0.06];
    var excess = 0.0;
    for (var j = -3; j <= 3; j++) {
      final index = ledge.groupIndex + j;
      if (index < 0 || index >= group.length) continue;
      final target = group[index];
      final next = target.depth + amount * weights[j + 3];
      excess += math.max(0.0, next - target.limit);
      target.depth = math.min(target.limit, next);
    }
    // Local redistribution suppresses thin spikes without a per-frame blur.
    for (var pass = 0; pass < 2; pass++) {
      for (var j = math.max(0, ledge.groupIndex - 4);
          j < math.min(group.length - 1, ledge.groupIndex + 4);
          j++) {
        final a = group[j], b = group[j + 1];
        final transfer = (a.depth - b.depth) * 0.25;
        a.depth -= transfer;
        b.depth += transfer;
      }
    }
    if (excess > 0.08) {
      for (var j = math.max(0, ledge.groupIndex - 2);
          j <= math.min(group.length - 1, ledge.groupIndex + 2);
          j++) {
        group[j].depth *= 0.7;
      }
      _fragment(ledge.x, ledge.y - ledge.depth - 1,
          _random.nextDouble() * 25 - 12, 8, 2);
    }
    _level(group);
    _capsDirty = true;
  }

  void _level(List<SnowLedge> group) {
    for (var pass = 0; pass < 4; pass++) {
      for (var j = 0; j < group.length - 1; j++) {
        final i = pass.isEven ? j : group.length - 2 - j;
        final a = group[i], b = group[i + 1];
        final difference = a.depth - b.depth;
        if (difference.abs() > 0.6) {
          final transfer = (difference - difference.sign * 0.6) * 0.5;
          a.depth -= transfer;
          b.depth += transfer;
        }
      }
    }
  }

  void _simulate(double dt) {
    _phase += dt;
    physicsSteps++;
    final decay = math.exp(-1.4 * dt), drag = math.exp(-0.8 * dt);
    final settleDrag = math.exp(-0.35 * dt);
    if (_floorMoving) {
      floorOffset += _floorSpeed * dt;
      _floorSpeed *= math.exp(-2.8 * dt);
      if (!floorVisible || _floorSpeed.abs() < 0.3) {
        _floorMoving = false;
        _floorSpeed = 0;
      }
    }
    final count = particles.length;
    for (var i = count - 1; i >= 0; i--) {
      final p = particles[i];
      if (lightweight && !p.debris) continue;
      final previousY = p.y;
      p.previousX = p.x;
      p.previousY = p.y;
      p.age += dt;
      if (p.energy > 0.1) {
        p.energy *= decay;
        p.vx += math.sin(p.phase + p.age * 5.1) * p.energy * dt * 2.4;
        p.vy += math.cos(p.phase * 1.7 + p.age * 4.3) * p.energy * dt * 1.8;
      } else {
        p.energy = 0;
      }
      if (p.debris) {
        p.vy += 105 * dt;
        p.vx *= drag;
      } else {
        p.vy += (22 + p.radius * 6 - p.vy) * dt;
        p.vx *= settleDrag;
      }
      p.x +=
          (p.vx + (p.debris ? 0 : math.sin(_phase * 0.6 + p.phase) * 5)) * dt;
      p.y += p.vy * dt;
      if (p.x < -12 ||
          p.x > size.width + 12 ||
          p.y > size.height + 8 ||
          p.y < -180 ||
          p.debris && p.age > 5) {
        if (p.debris) {
          _retire(i);
        } else {
          _recycle(p);
        }
        continue;
      }
      final bin = (p.x / step).floor().clamp(0, columns.length - 1);
      var landed = false;
      if (p.vy > 0 && (!p.debris || p.age > 0.35)) {
        for (final ledge in columns[bin]) {
          if (ledge.y >= size.height - floorHeightAt(p.x)) break;
          final top = ledge.y - ledge.depth;
          if (previousY + p.radius <= top && p.y + p.radius >= top) {
            _deposit(ledge, p.debris ? 0.7 : 0.8);
            // Most background flakes continue below the logo instead of all recycling at the top.
            landed = p.debris || _random.nextDouble() < 0.2;
            break;
          }
        }
      }
      if (landed || p.y + p.radius >= size.height - floorHeightAt(p.x)) {
        if (p.debris) {
          _retire(i);
        } else {
          _recycle(p);
        }
      }
    }
  }

  void sweep(Offset from, Offset to, double seconds) {
    if (!ready ||
        !canSweep(from) ||
        protectedAreas.any((area) => area.contains(to))) return;
    final delta = to - from, length2 = (to - from).distanceSquared;
    if (length2 < 0.5) return;
    final velocity = delta / math.max(seconds, 0.008);
    final speed = velocity.distance.clamp(0.0, 1000.0);
    final sweepingFloor = from.dy >= size.height - floorMaxHeight &&
        to.dy >= size.height - floorMaxHeight;
    final touchedCaps = <List<SnowLedge>>{};
    final radius = 22.0 + speed * 0.008;
    double distance(double x, double y) {
      final t = ((x - from.dx) * delta.dx + (y - from.dy) * delta.dy) / length2;
      final q = from + delta * t.clamp(0.0, 1.0);
      return math.sqrt((x - q.dx) * (x - q.dx) + (y - q.dy) * (y - q.dy));
    }

    if (lightweight) {
      tileHole = Rect.fromCircle(center: to, radius: radius + 5);
      _holeTime = 0.3;
      for (final flake in tileFlakes) {
        final point = tilePosition(flake);
        if (distance(point.dx, point.dy) < radius &&
            debrisCount < maxDebris &&
            _liftedFlakes.add(flake)) {
          _fragment(point.dx, point.dy, velocity.dx.clamp(-300.0, 300.0) * 0.5,
              -20 + velocity.dy.clamp(-100.0, 100.0) * 0.2, 1);
          particles.last.radius = flake.radius;
        }
      }
    }

    for (final p in particles) {
      final d = distance(p.x, p.y);
      if (d >= radius) continue;
      final force = 1 - d / radius, variation = 0.45 + _random.nextDouble();
      final spin = _random.nextDouble() * math.pi * 2;
      p.vx += (velocity.dx.clamp(-330.0, 330.0) * 0.42 * variation +
              math.cos(spin) * speed * 0.22) *
          force;
      p.vy += (velocity.dy.clamp(-240.0, 240.0) * 0.22 +
              math.sin(spin) * speed * 0.2 -
              30) *
          force;
      p.energy = math.min(150, p.energy + speed * force * 0.18);
      p.vx = p.vx.clamp(-450.0, 450.0);
      p.vy = p.vy.clamp(-300.0, 350.0);
    }
    final first = ((math.min(from.dx, to.dx) - radius) / step)
        .floor()
        .clamp(0, columns.length - 1);
    final last = ((math.max(from.dx, to.dx) + radius) / step)
        .ceil()
        .clamp(0, columns.length - 1);
    var launched = 0;
    for (var i = first; i <= last; i++) {
      for (final ledge in columns[i]) {
        if (sweepingFloor) break;
        if (distance(ledge.x, ledge.y - ledge.depth / 2) > radius ||
            ledge.depth < 0.3) continue;
        if (launched < 18 && i % 4 == 0) {
          _fragment(ledge.x, ledge.y - ledge.depth - 1,
              velocity.dx.clamp(-240.0, 240.0) * 0.4, -25 - speed * 0.06, 2);
          launched += 2;
        }
        ledge.depth *= 0.18;
        touchedCaps.add(ledge.group!);
        _capsDirty = true;
      }
    }
    for (final group in touchedCaps) {
      _level(group);
    }
    if (floorVisible && sweepingFloor) {
      // Translate a cohesive bank; never pile height columns against a hard ceiling.
      floorOffset += delta.dx;
      _floorSpeed = velocity.dx.clamp(-900.0, 900.0);
      _floorMoving = floorVisible && _floorSpeed.abs() > 0.3;
    }
    _notifyFrame(0, immediate: true);
  }

  List<Path> get capPaths {
    if (!_capsDirty) return _capPaths;
    _capPaths.clear();
    for (final group in capGroups) {
      if (!group.any((ledge) => ledge.depth > 0.15)) continue;
      final first = group.first, last = group.last;
      final cap = Path()
        ..moveTo(first.x - 1, first.y)
        ..quadraticBezierTo(
            first.x - 1, first.y - first.depth, first.x, first.y - first.depth);
      for (var i = 1; i < group.length; i++) {
        final a = group[i - 1], b = group[i];
        cap.quadraticBezierTo(a.x, a.y - a.depth, (a.x + b.x) / 2,
            (a.y - a.depth + b.y - b.depth) / 2);
      }
      cap
        ..lineTo(last.x, last.y - last.depth)
        ..quadraticBezierTo(
            last.x + 1, last.y - last.depth, last.x + 1, last.y);
      for (final ledge in group.reversed) {
        cap.lineTo(ledge.x, ledge.y);
      }
      _capPaths.add(cap..close());
    }
    _capsDirty = false;
    return _capPaths;
  }
}

enum SnowLayer { all, settled, particles }

class SnowPainter extends CustomPainter {
  final SnowField field;
  final bool dark;
  final SnowLayer layer;
  final bool batched;
  late final List<Float32List> _points = List.generate(60,
      (_) => Float32List((SnowField.fallingCount + SnowField.maxDebris) * 2));
  late final List<int> _pointCounts = List.filled(60, 0);
  late final List<Paint> _pointPaints = List.generate(
      60,
      (i) => Paint()
        ..color = (dark ? const Color(0xfff2f6ff) : const Color(0xffafc5da))
            .withOpacity((i ~/ 5) / 12)
        ..strokeWidth = 2 * (0.8 + (i % 5) * 0.6)
        ..strokeCap = StrokeCap.round);
  late final Paint _cap = Paint()
    ..color = dark ? const Color(0xfff1f6fc) : const Color(0xffe2ebf4);
  final Paint _shadow = Paint()..color = const Color(0x388fa4ba);
  late final List<Paint> _flakes = List.generate(
      12,
      (i) => Paint()
        ..color = (dark ? const Color(0xfff2f6ff) : const Color(0xffafc5da))
            .withOpacity(i / 12));
  Paint? _floorPaint;
  Path? _floorPath;
  List<double>? _floorSource;
  Size? _shaderSize;
  SnowPainter(this.field, this.dark,
      {this.layer = SnowLayer.all, this.batched = false})
      : super(repaint: layer == SnowLayer.settled ? field.settled : field);
  @override
  void paint(Canvas canvas, Size size) {
    if (!field.ready) return;
    if (layer != SnowLayer.settled) field.particlePaints++;
    if (layer != SnowLayer.particles) field.settledPaints++;
    canvas.save();
    canvas.clipRect(Offset.zero & size);
    if (layer != SnowLayer.particles) {
      for (final path in field.capPaths) {
        canvas.save();
        canvas.translate(0, 0.4);
        canvas.drawPath(path, _shadow);
        canvas.restore();
        canvas.drawPath(path, _cap);
      }
    }
    final alpha = field.renderAlpha;
    if (layer != SnowLayer.settled) {
      if (batched) {
        _pointCounts.fillRange(0, _pointCounts.length, 0);
        for (final p in field.particles) {
          if (field.lightweight && !p.debris) continue;
          final opacity = p.debris
              ? (1 - p.age / 5).clamp(0.0, 0.9)
              : 0.55 + p.radius * 0.15;
          final bucket = (opacity * 11).round().clamp(0, 11) * 5 +
              ((p.radius - 0.8) / 0.6).round().clamp(0, 4);
          final index = _pointCounts[bucket];
          _points[bucket][index] = p.previousX + (p.x - p.previousX) * alpha;
          _points[bucket][index + 1] =
              p.previousY + (p.y - p.previousY) * alpha;
          _pointCounts[bucket] += 2;
        }
        for (var i = 0; i < _pointCounts.length; i++) {
          if (_pointCounts[i] > 0) {
            canvas.drawRawPoints(
                PointMode.points,
                Float32List.sublistView(_points[i], 0, _pointCounts[i]),
                _pointPaints[i]);
          }
        }
      } else {
        for (final p in field.particles) {
          if (field.lightweight && !p.debris) continue;
          final opacity = p.debris
              ? (1 - p.age / 5).clamp(0.0, 0.9)
              : 0.55 + p.radius * 0.15;
          final paint = _flakes[(opacity * 11).round().clamp(0, 11)];
          // Interactive rectangles affect gesture hit testing, never snow visibility.
          canvas.drawCircle(
              Offset(p.previousX + (p.x - p.previousX) * alpha,
                  p.previousY + (p.y - p.previousY) * alpha),
              p.radius,
              paint);
        }
      }
    }
    if (layer == SnowLayer.particles) {
      canvas.restore();
      return;
    }
    if (_floorPath == null || !identical(_floorSource, field.floor)) {
      final fresh = Path()..moveTo(0, size.height);
      for (var i = 0; i < field.floor.length; i++) {
        final h = field.previousFloor[i] +
            (field.floor[i] - field.previousFloor[i]) * alpha;
        fresh.lineTo(i * SnowField.step, size.height - h);
      }
      fresh
        ..lineTo(size.width, size.height - field.floor.last)
        ..lineTo(size.width, size.height)
        ..close();
      _floorPath = fresh;
      _floorSource = field.floor;
    }
    if (_shaderSize != size) {
      _shaderSize = size;
      _floorPaint = Paint()
        ..shader = Gradient.linear(
            Offset(0, size.height - SnowField.floorMaxHeight),
            Offset(0, size.height),
            dark
                ? [const Color(0xfff9fcff), const Color(0xffbecddd)]
                : [const Color(0xfff8fbff), const Color(0xffc0d0df)]);
    }
    if (field.floorVisible) {
      canvas.save();
      canvas.translate(field.floorOffset, 0);
      canvas.drawPath(_floorPath!, _floorPaint!);
      canvas.restore();
    }
    canvas.restore();
  }

  @override
  bool shouldRepaint(SnowPainter oldDelegate) =>
      oldDelegate.dark != dark ||
      oldDelegate.field != field ||
      oldDelegate.layer != layer ||
      oldDelegate.batched != batched;
}
