import 'dart:math' show min;
import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../common.dart' show isDesktop;
import 'platform_model.dart' show bind;
import '../common/widgets/peer_card.dart' show peerCardUiType, PeerUiType;

const rdgenSlimUiKey = 'rdgen-slim-ui-v1';
final rdgenSlimUi =
    (isDesktop && bind.mainGetLocalOption(key: rdgenSlimUiKey) != 'N').obs;

bool get rdgenSlimList => rdgenSlimUi.value && peerCardUiType.value == PeerUiType.list;

Future<void> setRdgenSlimUi(bool value) async {
  await bind.mainSetLocalOption(key: rdgenSlimUiKey, value: value ? 'Y' : 'N');
  rdgenSlimUi.value = value;
}

class RdgenConnectionLayout extends StatelessWidget {
  final List<Widget> children;
  const RdgenConnectionLayout({super.key, required this.children});

  @override
  Widget build(BuildContext context) {
    if (!rdgenSlimUi.value) return Column(children: children);
    return LayoutBuilder(builder: (context, constraints) {
      final input = SizedBox(width: min(280.0, constraints.maxWidth), child: children[1]);
      final actions = IntrinsicWidth(child: children[2]);
      return Column(mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          children[0],
          IntrinsicHeight(child: Row(crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [Flexible(child: input), const SizedBox(width: 12), actions])),
        ]);
    });
  }
}
