import 'dart:math' show min;
import 'package:flutter/material.dart';
import 'package:get/get.dart';
import 'package:url_launcher/url_launcher.dart';
import '../common.dart' show isDesktop, gFFI, translate;
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
      final field = SizedBox(
        width: min(280.0, constraints.maxWidth),
        child: Column(mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [children[0], SizedBox(height: 44, child: children[1])]),
      );
      final actions = IntrinsicWidth(child: children[2]);
      final account = SizedBox(width: min(200.0, constraints.maxWidth),
        child: Obx(() => Column(mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.end,
          children: [
            Row(mainAxisSize: MainAxisSize.min, children: [
              const Icon(Icons.person_outline, size: 16),
              const SizedBox(width: 6),
              Flexible(child: Text(gFFI.userModel.isLogin
                ? gFFI.userModel.displayNameOrUserName : translate('Not signed in'),
                maxLines: 1, overflow: TextOverflow.ellipsis)),
            ]),
            const SizedBox(height: 8),
            OutlinedButton.icon(
              onPressed: () async {
                var opened = false;
                try {
                  opened = await launchUrl(Uri.parse('https://desk.status16.ru/login'),
                    mode: LaunchMode.externalApplication);
                } catch (_) {
                  opened = false;
                }
                if (!opened && context.mounted) {
                  ScaffoldMessenger.maybeOf(context)?.showSnackBar(
                    const SnackBar(content: Text('https://desk.status16.ru/login')));
                }
              },
              icon: const Icon(Icons.open_in_new, size: 16),
              label: Text(translate('Open web panel')),
            ),
          ],
        )),
      );
      if (constraints.maxWidth >= 760) {
        return Row(crossAxisAlignment: CrossAxisAlignment.end,
          children: [field, const SizedBox(width: 12), actions,
            const Spacer(), account]);
      }
      return Column(mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Wrap(spacing: 12, runSpacing: 12,
            crossAxisAlignment: WrapCrossAlignment.end,
            children: [field, actions]),
          const SizedBox(height: 12),
          Align(alignment: Alignment.centerRight, child: account),
        ]);
    });
  }
}
