import 'dart:async';
import 'dart:math' as math;
import 'dart:typed_data';
import 'dart:ui' show PointMode;
import 'package:flutter/material.dart';

const rdgenWinterBackground = Color(0xff24252b);

class RdgenWinterScene extends StatefulWidget {
  final GlobalKey contentKey;
  final ScrollController scrollController;
  final Widget child;
  const RdgenWinterScene(
      {super.key,
      required this.contentKey,
      required this.scrollController,
      required this.child});

  @override
  State<RdgenWinterScene> createState() => _RdgenWinterSceneState();
}

class _RdgenWinterSceneState extends State<RdgenWinterScene> {
  double protectedHeight = double.infinity;
  bool measurePending = false;

  @override
  void initState() {
    super.initState();
    widget.scrollController.addListener(measureContent);
    measureContent();
  }

  void measureContent() {
    if (measurePending) return;
    measurePending = true;
    WidgetsBinding.instance.addPostFrameCallback((_) {
      measurePending = false;
      if (!mounted) return;
      final content = widget.contentKey.currentContext?.findRenderObject();
      if (content is! RenderBox || !content.hasSize) return;
      final offset = widget.scrollController.hasClients
          ? widget.scrollController.offset
          : 0.0;
      final height = math.max(0.0, content.size.height - offset);
      if ((height - protectedHeight).abs() > 0.5) {
        setState(() => protectedHeight = height);
      }
    });
  }

  @override
  void didUpdateWidget(RdgenWinterScene oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.scrollController != widget.scrollController) {
      oldWidget.scrollController.removeListener(measureContent);
      widget.scrollController.addListener(measureContent);
    }
    measureContent();
  }

  @override
  void dispose() {
    widget.scrollController.removeListener(measureContent);
    super.dispose();
  }

  @override
  Widget build(BuildContext context) =>
      NotificationListener<SizeChangedLayoutNotification>(onNotification: (_) {
        measureContent();
        return false;
      }, child: LayoutBuilder(builder: (context, constraints) {
        final height = constraints.maxHeight;
        final start =
            height > 0 ? (protectedHeight / height).clamp(0.0, 1.0) : 1.0;
        final end = height > 0
            ? ((protectedHeight + 80) / height).clamp(0.0, 1.0)
            : 1.0;
        return ClipRect(
            child: Stack(fit: StackFit.expand, children: [
          IgnorePointer(
              child: RepaintBoundary(
                  child: Stack(children: [
            Positioned(
                bottom: 0,
                left: 0,
                right: 0,
                height: 230,
                child: Image.asset('assets/rdgen-winter-forest.png',
                    cacheWidth: 600,
                    fit: BoxFit.cover,
                    alignment: Alignment.bottomCenter)),
            const Positioned(
                bottom: 0,
                left: 0,
                right: 0,
                height: 32,
                child: CustomPaint(painter: _WinterGround())),
            Positioned(
                bottom: 10,
                right: -10,
                width: 145,
                height: 252,
                child: Image.asset('assets/rdgen-winter-tree.png',
                    cacheWidth: 435,
                    fit: BoxFit.contain,
                    alignment: Alignment.bottomRight)),
            Positioned.fill(
                child: DecoratedBox(
                    decoration: BoxDecoration(
                        gradient: LinearGradient(
                            begin: Alignment.topCenter,
                            end: Alignment.bottomCenter,
                            colors: const [
                  rdgenWinterBackground,
                  rdgenWinterBackground,
                  Color(0x0024252b)
                ],
                            stops: [
                  0,
                  start,
                  end
                ])))),
          ]))),
          const Positioned.fill(child: IgnorePointer(child: _WinterSnow())),
          widget.child,
        ]));
      }));
}

class _WinterGround extends CustomPainter {
  const _WinterGround();
  @override
  void paint(Canvas canvas, Size size) {
    final path = Path()
      ..moveTo(0, size.height)
      ..lineTo(0, 12)
      ..quadraticBezierTo(size.width * .25, 0, size.width * .5, 14)
      ..quadraticBezierTo(size.width * .8, 25, size.width, 9)
      ..lineTo(size.width, size.height)
      ..close();
    canvas.drawPath(path, Paint()..color = const Color(0xffe5edf4));
  }

  @override
  bool shouldRepaint(_WinterGround oldDelegate) => false;
}

class _WinterSnow extends StatefulWidget {
  const _WinterSnow();
  @override
  State<_WinterSnow> createState() => _WinterSnowState();
}

class _WinterSnowState extends State<_WinterSnow> with WidgetsBindingObserver {
  final field = _WinterSnowField();
  final clock = Stopwatch();
  Timer? timer;
  Duration previous = Duration.zero;
  Size size = Size.zero;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    updateTimer();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) => updateTimer();

  void updateTimer() {
    final lifecycle = WidgetsBinding.instance.lifecycleState;
    final visible = lifecycle == null ||
        lifecycle == AppLifecycleState.resumed ||
        lifecycle == AppLifecycleState.inactive;
    final enabled = visible && TickerMode.of(context);
    if (enabled == (timer != null)) return;
    timer?.cancel();
    timer = null;
    clock.stop();
    if (!enabled) return;
    previous = clock.elapsed;
    clock.start();
    timer = Timer.periodic(const Duration(microseconds: 33333), (_) {
      final elapsed = clock.elapsed;
      final delta = elapsed - previous;
      previous = elapsed;
      field.advance(math.min(delta.inMicroseconds / 1000000, 0.1), size);
    });
  }

  @override
  void dispose() {
    timer?.cancel();
    clock.stop();
    WidgetsBinding.instance.removeObserver(this);
    field.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) =>
      LayoutBuilder(builder: (context, constraints) {
        size = constraints.biggest;
        return RepaintBoundary(
            child: CustomPaint(painter: _WinterSnowPainter(field)));
      });
}

class _WinterSnowField extends ChangeNotifier {
  final random = math.Random(71239);
  final points = Float32List(64);
  final y = Float32List(32);
  final x = Float32List(32);
  final speed = Float32List(32);
  final paint = Paint()
    ..color = const Color(0xbbeef4ff)
    ..strokeWidth = 1.6
    ..strokeCap = StrokeCap.round;

  _WinterSnowField() {
    for (var i = 0; i < y.length; i++) {
      x[i] = random.nextDouble();
      y[i] = random.nextDouble();
      speed[i] = 18 + random.nextDouble() * 16;
    }
  }

  void advance(double seconds, Size size) {
    if (size.isEmpty) return;
    for (var i = 0; i < y.length; i++) {
      y[i] += seconds * speed[i] / size.height;
      if (y[i] > 1) {
        y[i] -= 1;
        x[i] = random.nextDouble();
      }
    }
    notifyListeners();
  }
}

class _WinterSnowPainter extends CustomPainter {
  final _WinterSnowField field;
  _WinterSnowPainter(this.field) : super(repaint: field);
  @override
  void paint(Canvas canvas, Size size) {
    for (var i = 0; i < field.y.length; i++) {
      field.points[i * 2] = field.x[i] * size.width;
      field.points[i * 2 + 1] = field.y[i] * size.height;
    }
    canvas.drawRawPoints(PointMode.points, field.points, field.paint);
  }

  @override
  bool shouldRepaint(_WinterSnowPainter oldDelegate) =>
      oldDelegate.field != field;
}
