void main() {
  for (final mode in [Brightness.light, Brightness.dark]) {
    testWidgets('Generated native toolbar keeps RustDesk theme extensions: $mode', (tester) async {
      tester.binding.platformDispatcher.accessibilityFeaturesTestValue = const FakeAccessibilityFeatures(disableAnimations: true);
      addTearDown(tester.binding.platformDispatcher.clearAccessibilityFeaturesTestValue);
      final extension = mode == Brightness.light ? ColorThemeExtension.light : ColorThemeExtension.dark;
      final theme = (mode == Brightness.light ? ThemeData.light() : ThemeData.dark()).copyWith(extensions: [extension]);
      var remoteClicks = 0;
      Widget host(bool collapsed) => MaterialApp(theme: theme, home: Scaffold(body: Stack(children: [
        Positioned.fill(child: GestureDetector(onTap: () { remoteClicks++; }, child: Container(color: Colors.blueGrey))),
        Positioned.fill(child: RdgenCompactSessionToolbar(collapsed: collapsed, assigned: true,
          onExpand: () {}, onChoose: () {}, child: Row(mainAxisSize: MainAxisSize.min, children: [
            _IconMenuButton(icon: const Icon(Icons.push_pin), tooltip: 'Pin Toolbar', color: Colors.grey, hoverColor: Colors.grey, onPressed: () {}),
            _IconMenuButton(icon: const RdgenToolbarGlyph('fullscreen'), tooltip: 'Fullscreen', color: Colors.grey, hoverColor: Colors.grey, onPressed: () {}),
            _IconMenuButton(icon: const Icon(Icons.close), tooltip: 'Close', color: Colors.grey, hoverColor: Colors.grey, onPressed: () {}),
            for (final label in ['Display Settings', 'Keyboard Settings', 'Control Actions'])
              _IconSubmenuButton(icon: const Icon(Icons.settings_outlined), tooltip: label,
                color: Colors.grey, hoverColor: Colors.grey, menuChildrenGetter: (_) => [
                  MenuItemButton(onPressed: () {}, child: const Text('Native action'))]),
            Builder(builder: (context) {
              expect(Theme.of(context).extension<ColorThemeExtension>(), same(extension));
              expect(Theme.of(context).brightness, mode);
              expect(rdgenToolbarSurface(context), mode == Brightness.dark ? const Color(0xff22252b) : const Color(0xfff5f6f8));
              return const SizedBox();
            }),
          ]))),
      ])));
      await tester.pumpWidget(host(false));
      await tester.pumpAndSettle();
      expect(tester.takeException(), isNull);
      expect(find.byType(ErrorWidget), findsNothing);
      for (final label in ['Pin Toolbar', 'Fullscreen', 'Close']) {
        final face = find.descendant(of: find.byWidgetPredicate((w) => w is _IconMenuButton && w.tooltip == label), matching: find.byType(Ink));
        expect(tester.getSize(face), const Size(30, 30), reason: label);
      }
      await tester.tap(find.byTooltip('Display Settings').first);
      await tester.pumpAndSettle();
      expect(find.text('Native action'), findsOneWidget);
      await tester.tap(find.text('Native action'));
      await tester.pumpAndSettle();
      await tester.tapAt(const Offset(100, 400));
      expect(remoteClicks, 1);
      await tester.pumpWidget(host(true));
      await tester.pumpAndSettle();
      expect(tester.takeException(), isNull);
      expect(find.byType(ErrorWidget), findsNothing);
    });
  }
  testWidgets('Slow and unsupported organization APIs cannot hide the native controls or remote surface', (tester) async {
    final controller = RdgenSessionOrganization();
    final response = Completer<WorkGroupReply>();
    late OverlayDialogManager manager;
    var remoteClicks = 0;
    Widget host({bool authenticated = true}) => MaterialApp(
      theme: ThemeData.light().copyWith(extensions: [ColorThemeExtension.light]),
      home: Builder(builder: (context) {
        manager = OverlayDialogManager(context);
        return Scaffold(body: Stack(children: [
          Positioned.fill(child: GestureDetector(onTap: () { remoteClicks++; }, child: Container(color: Colors.blueGrey))),
          Positioned.fill(child: ListenableBuilder(listenable: controller, builder: (_, __) =>
            RdgenCompactSessionToolbar(collapsed: false, assigned: true, onExpand: () {}, onChoose: () {},
              child: Row(mainAxisSize: MainAxisSize.min, children: [
                _IconSubmenuButton(icon: const Icon(Icons.settings_outlined), tooltip: 'Display Settings',
                  color: Colors.grey, hoverColor: Colors.grey, menuChildrenGetter: (_) => [MenuItemButton(onPressed: () {}, child: const Text('Native action'))]),
                RdgenOrganizationSessionMenu(organization: controller, manager: manager, current: () => true, authenticated: authenticated),
              ])))),
        ]));
      }));
    await tester.pumpWidget(host());
    final pending = controller.attach(WorkGroupSession(Uri.parse('https://console.test/api/audit/conn/active'),
      '123', '987', 0, 'token', (_, uri, __, ___) async => uri.path.endsWith('/active')
        ? WorkGroupReply(200, '"guid"') : response.future, () => true), manager, () => true);
    await tester.pumpAndSettle();
    expect(find.text('Loading organizations…'), findsOneWidget);
    await tester.tap(find.byTooltip('Display Settings').first);
    await tester.pumpAndSettle();
    expect(find.text('Native action'), findsOneWidget);
    await tester.tap(find.text('Native action'));
    await tester.pumpAndSettle();
    await tester.tapAt(const Offset(100, 400));
    expect(remoteClicks, 1);
    response.complete(WorkGroupReply(404, '{}'));
    await tester.pumpAndSettle();
    await pending;
    expect(find.text('Organizations unavailable'), findsOneWidget);
    expect(find.byType(ErrorWidget), findsNothing);
    expect(tester.takeException(), isNull);
    await tester.pumpWidget(host(authenticated: false));
    await tester.pumpAndSettle();
    expect(find.text('Sign in to select an organization'), findsOneWidget);
    expect(find.byTooltip('Display Settings'), findsWidgets);
    await tester.pumpWidget(const SizedBox());
    controller.dispose();
  });

}
