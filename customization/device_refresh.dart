import '../common.dart';
import 'platform_model.dart';
import '../utils/multi_window_manager.dart';

Future<void> Function(String)? rdgenRefreshVisibleDevice;

Future<void> rdgenNotifyDeviceChanged(Uri base, String peer) async {
  if (!isDesktop) return;
  // The main window owns the lists; remote windows have separate Dart engines.
  try {
    await rustDeskWinManager.call(WindowType.Main, 'rdgen-device-changed', {
      'id': peer, 'server': base.toString(),
      'account': bind.mainGetLocalOption(key: 'user_info'),
    });
  } catch (_) {
    debugPrint('Device list notification unavailable; use Refresh to reload');
  }
}
