import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../common.dart' show isDesktop;
import 'platform_model.dart' show bind;

const rdgenSlimUiKey = 'rdgen-slim-ui-v1';
final rdgenSlimUi =
    (isDesktop && bind.mainGetLocalOption(key: rdgenSlimUiKey) == 'Y').obs;

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
      if (constraints.maxWidth < 520) return Column(children: children);
      return Row(
        crossAxisAlignment: CrossAxisAlignment.end,
        children: [
          Expanded(child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [children[0], children[1]],
          )),
          const SizedBox(width: 12),
          IntrinsicWidth(child: children[2]),
        ],
      );
    });
  }
}
