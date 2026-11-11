import 'package:flutter/material.dart';
import 'package:get/get.dart';
import 'package:url_launcher/url_launcher.dart';
import '../common/widgets/login.dart' show loginDialog;
import '../common.dart' show gFFI, translate;

class RdgenAccountGroup extends StatelessWidget {
  final Widget child;
  final bool compact;
  const RdgenAccountGroup({super.key, required this.child, this.compact = false});

  @override
  Widget build(BuildContext context) {
    return Row(crossAxisAlignment: CrossAxisAlignment.center, children: [
      Expanded(child: Align(alignment: Alignment.centerLeft,
        child: ConstrainedBox(
          constraints: BoxConstraints(maxWidth: compact ? double.infinity : 320),
          child: child))),
      const SizedBox(width: 20),
      Container(width: 1, height: 64, color: Theme.of(context).dividerColor),
      const SizedBox(width: 16),
      const SizedBox(width: 174, child: RdgenDesktopAccount()),
    ]);
  }
}

class RdgenDesktopAccount extends StatelessWidget {
  const RdgenDesktopAccount({super.key});

  @override
  Widget build(BuildContext context) {
    return Obx(() => Column(mainAxisSize: MainAxisSize.min,
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
        if (!gFFI.userModel.isLogin)
          OutlinedButton.icon(
            onPressed: loginDialog,
            icon: const Icon(Icons.login, size: 16),
            label: Text(translate('Login')),
          )
        else OutlinedButton(
          style: OutlinedButton.styleFrom(
            minimumSize: const Size(0, 32),
            padding: const EdgeInsets.symmetric(horizontal: 10),
            alignment: Alignment.center,
            tapTargetSize: MaterialTapTargetSize.shrinkWrap),
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
          child: Text(translate('Open web panel'), textAlign: TextAlign.center),
        ),
      ],
    ));
  }
}
