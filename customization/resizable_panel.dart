import 'dart:math' as math;
import 'package:flutter/material.dart';

class RdgenResizablePanel extends StatefulWidget {
  final double initialWidth;
  final double availableWidth;
  final String Function() readWidth;
  final Future<void> Function(String) saveWidth;
  final Widget Function(double) builder;
  final String restoreLabel;

  const RdgenResizablePanel({Key? key, required this.initialWidth,
    required this.availableWidth, required this.readWidth, required this.saveWidth,
    required this.builder, required this.restoreLabel}) : super(key: key);

  @override
  State<RdgenResizablePanel> createState() => _RdgenResizablePanelState();
}

class _RdgenResizablePanelState extends State<RdgenResizablePanel> {
  late double _preferredWidth;

  @override
  void initState() {
    super.initState();
    final stored = double.tryParse(widget.readWidth());
    _preferredWidth = stored != null && stored.isFinite
        ? stored.clamp(150.0, 480.0).toDouble() : widget.initialWidth;
  }

  double _constrained(double preferred) {
    final available = widget.availableWidth.isFinite ? widget.availableWidth : 960.0;
    final reserve = math.min(240.0, available / 2);
    final maximum = math.max(0.0, math.min(480.0, available - reserve - 20.0));
    return preferred.clamp(math.min(150.0, maximum), maximum).toDouble();
  }

  @override
  Widget build(BuildContext context) {
    final width = _constrained(_preferredWidth);
    return Row(mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        widget.builder(width),
        MouseRegion(cursor: SystemMouseCursors.resizeColumn,
          child: Tooltip(message: widget.restoreLabel,
            child: GestureDetector(
              key: const ValueKey('rdgen-panel-handle'),
              behavior: HitTestBehavior.opaque,
              onHorizontalDragUpdate: (details) => setState(() {
                final delta = Directionality.of(context) == TextDirection.rtl
                    ? -details.delta.dx : details.delta.dx;
                _preferredWidth = _constrained(_constrained(_preferredWidth) + delta);
              }),
              onHorizontalDragEnd: (_) async {
                await widget.saveWidth(_preferredWidth.round().toString());
              },
              onDoubleTap: () async {
                setState(() => _preferredWidth = widget.initialWidth);
                await widget.saveWidth('');
              },
              child: SizedBox(width: 8,
                child: Center(child: Container(width: 2, height: 32,
                  decoration: BoxDecoration(color: Theme.of(context).dividerColor,
                    borderRadius: BorderRadius.circular(1))))),
            ),
          ),
        ),
      ],
    );
  }
}
