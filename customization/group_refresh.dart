import 'dart:async';

/// One refresh per account/server; joining callers await the same result.
class RdgenGroupRefresh {
  Future<void>? _pending;
  String? scope;
  DateTime? catalogAt;
  Future<void> get settled => _pending ?? Future<void>.value();
  bool get catalogFresh => catalogAt != null &&
      DateTime.now().difference(catalogAt!) < const Duration(hours: 12);

  Future<void> run(String owner, Future<void> Function() action,
      {bool catalog = false}) {
    final pending = _pending;
    if (pending != null) {
      if (scope == owner) return pending;
      return pending.then((_) => run(owner, action, catalog: catalog),
          onError: (Object _, StackTrace __) => run(owner, action, catalog: catalog));
    }
    if (scope != owner || catalog) catalogAt = null;
    scope = owner;
    final next = Future<void>.sync(action).whenComplete(() { _pending = null; });
    _pending = next;
    return next;
  }
}
