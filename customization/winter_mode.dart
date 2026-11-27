import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../common.dart' show MyTheme, isDesktop, isInHomePage;
import 'platform_model.dart' show bind;
import 'rdgen_winter_scene.dart';

const rdgenWinterModeKey = 'rdgen-winter-mode-v1';
final rdgenWinterMode =
    (isDesktop && bind.mainGetLocalOption(key: rdgenWinterModeKey) == 'Y').obs;

Future<void> setRdgenWinterMode(bool enabled) async {
  await bind.mainSetLocalOption(
      key: rdgenWinterModeKey, value: enabled ? 'Y' : 'N');
  rdgenWinterMode.value = enabled;
}

class RdgenWinterPane extends StatelessWidget {
  final WidgetBuilder builder;
  const RdgenWinterPane({super.key, required this.builder});

  @override
  Widget build(BuildContext context) => Obx(() {
        if (!rdgenWinterMode.value) return builder(context);
        return TickerMode(
            enabled: isInHomePage(),
            child: Theme(
                data: MyTheme.darkTheme.copyWith(
                    scaffoldBackgroundColor: rdgenWinterBackground,
                    colorScheme: MyTheme.darkTheme.colorScheme
                        .copyWith(background: rdgenWinterBackground)),
                child: Builder(builder: builder)));
      });
}

Widget rdgenWinterPanel({
  required GlobalKey contentKey,
  required ScrollController scrollController,
  required Widget child,
}) =>
    rdgenWinterMode.value
        ? RdgenWinterScene(
            contentKey: contentKey,
            scrollController: scrollController,
            child: child)
        : child;

Widget rdgenWinterObserve(Widget child) =>
    rdgenWinterMode.value ? SizeChangedLayoutNotifier(child: child) : child;

Widget rdgenWinterScroll(Widget child) =>
    rdgenWinterMode.value ? Expanded(child: child) : child;

class RdgenWinterLogo extends StatelessWidget {
  const RdgenWinterLogo({super.key});

  @override
  Widget build(BuildContext context) => Padding(
      padding: const EdgeInsets.fromLTRB(12, 12, 12, 0),
      child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 300, maxHeight: 64),
          child: Image.asset('assets/rdgen-winter-logo.png',
              cacheWidth: 600, fit: BoxFit.contain)));
}
