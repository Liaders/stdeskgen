import 'package:flutter/material.dart';
import 'package:get/get.dart';
import 'package:url_launcher/url_launcher.dart';
import '../common.dart' show gFFI, translate;

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
    ));
  }
}
