import 'dart:convert';
import '../common.dart' show isWindows, showToast, translate;
import 'platform_model.dart' show bind;
import 'state_model.dart' show stateGlobal;

const rdgenUpdatePrefix = 'statusdesk-update://available/';
bool _rdgenPolling = false;
String _rdgenUpdatePhase = 'idle';
bool _rdgenManualInstall = false;

Future<void> rdgenPollUpdateCard() async {
  if (_rdgenPolling || !isWindows || !bind.mainIsInstalled()) return;
  _rdgenPolling = true;
  try {
    final data = jsonDecode(await bind.mainGetCommon(key: 'rdgen-update-status')) as Map<String, dynamic>;
    _rdgenUpdatePhase = data['status'] as String? ?? 'idle';
    if (_rdgenManualInstall && _rdgenUpdatePhase == 'error') {
      showToast(translate(data['message'] as String? ?? 'Update service is unavailable'));
    }
    if (['error', 'current', 'installing'].contains(_rdgenUpdatePhase)) _rdgenManualInstall = false;
    final version = data['version'] as String? ?? '';
    if (['available', 'downloading', 'installing', 'error'].contains(_rdgenUpdatePhase) && version.isNotEmpty) {
      stateGlobal.updateUrl.value = rdgenUpdatePrefix + Uri.encodeComponent(version);
    } else if (_rdgenUpdatePhase == 'current') {
      stateGlobal.updateUrl.value = '';
    }
  } catch (_) {
    // A restarting/offline service leaves the last known card unchanged.
  } finally {
    _rdgenPolling = false;
  }
}

Future<void> rdgenInstallUpdate() async {
  if (['checking', 'downloading', 'installing'].contains(_rdgenUpdatePhase)) {
    showToast(translate(_rdgenUpdatePhase == 'installing'
        ? 'Starting update installation' : _rdgenUpdatePhase == 'checking'
        ? 'Checking for updates' : 'Downloading update'));
    return;
  }
  try {
    final data = jsonDecode(await bind.mainGetCommon(key: 'rdgen-update-install')) as Map<String, dynamic>;
    _rdgenUpdatePhase = data['status'] as String? ?? 'error';
    _rdgenManualInstall = _rdgenUpdatePhase == 'downloading';
    showToast(translate(_rdgenUpdatePhase == 'error'
        ? data['message'] as String? ?? 'Update service is unavailable'
        : _rdgenUpdatePhase == 'checking' ? 'Checking for updates' : 'Downloading update'));
  } catch (_) {
    showToast(translate('Update service is unavailable'));
  }
}
