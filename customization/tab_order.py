"""One-time desktop tab ordering, leaving upstream visibility preferences alone."""


def add_initial_order(replace, with_colleagues):
    model = 'flutter/lib/models/peer_tab_model.dart'
    order = [0, 1, 6, 5, 2, 4, 3] if with_colleagues else [0, 1, 5, 2, 4, 3]
    marker = f'rdgen-peer-tab-order-v1-{len(order)}'
    replace(model, '    // init currentTab', f'''    // rdgen initial tab order
    if (bind.getLocalFlutterOption(k: '{marker}') != 'Y') {{
      orders.setAll(0, {order});
      _rdgenSaveInitialTabOrder();
    }}
    // init currentTab''')
    replace(model, '  setCurrentTab(int index) {', f'''  Future<void> _rdgenSaveInitialTabOrder() async {{
    try {{
      await bind.setLocalFlutterOption(k: kOptionPeerTabOrder, v: jsonEncode(orders));
      await bind.setLocalFlutterOption(k: '{marker}', v: 'Y');
    }} catch (e) {{
      debugPrint('failed to save initial peer tab order: $e');
    }}
  }}

  setCurrentTab(int index) {{''')
