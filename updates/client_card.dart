import 'dart:async';
import 'dart:convert';
import 'package:flutter/material.dart';
import '../common.dart' show isWindows, translate;
import 'platform_model.dart' show bind;

class RdgenUpdateCard extends StatefulWidget {
  const RdgenUpdateCard({super.key});
  @override
  State<RdgenUpdateCard> createState() => _RdgenUpdateCardState();
}

class _RdgenUpdateCardState extends State<RdgenUpdateCard> {
  String _status = 'idle', _version = '', _message = '';
  Timer? _timer;
  bool get _busy => ['checking', 'downloading'].contains(_status);

  Future<void> _request(String command) async {
    _timer?.cancel();
    if (command != 'rdgen-update-status') {
      setState(() { _status = command == 'rdgen-update-install' ? 'downloading' : 'checking'; _message = ''; });
    }
    try {
      final raw = await bind.mainGetCommon(key: command);
      final data = jsonDecode(raw) as Map<String, dynamic>;
      if (!mounted) return;
      setState(() {
        _status = data['status'] as String? ?? 'error';
        _version = data['version'] as String? ?? '';
        _message = data['message'] as String? ?? '';
      });
    } catch (_) {
      if (!mounted) return;
      setState(() { _status = 'error'; _message = 'Update service is unavailable'; });
    }
    if (_busy) {
      _timer = Timer(const Duration(seconds: 1), () => _request('rdgen-update-status'));
    }
  }

  @override
  void dispose() { _timer?.cancel(); super.dispose(); }

  @override
  Widget build(BuildContext context) {
    if (!isWindows || !bind.mainIsInstalled() || bind.isDisableInstallation()) {
      return const SizedBox.shrink();
    }
    final labels = {
      'checking': 'Checking for updates', 'downloading': 'Downloading update',
      'installing': 'Starting update installation', 'current': 'Latest version installed',
      'available': 'New version available', 'error': 'Update check failed',
    };
    return Padding(padding: const EdgeInsets.fromLTRB(20, 8, 20, 12),
      child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
        if (_status != 'idle') Text(
          '${translate(labels[_status] ?? 'Update check failed')}${_status == 'available' ? ' $_version' : ''}',
          textAlign: TextAlign.center),
        if (_message.isNotEmpty) Tooltip(message: translate(_message),
          child: Text(translate(_message), maxLines: 3, overflow: TextOverflow.ellipsis)),
        if (_busy) const Padding(padding: EdgeInsets.only(top: 8), child: LinearProgressIndicator()),
        OutlinedButton(
          onPressed: _busy || _status == 'installing' ? null : () => _request(
            _status == 'available' ? 'rdgen-update-install' : 'rdgen-update-check'),
          child: Text(translate(_status == 'available' ? 'Update' : 'Check for updates'), textAlign: TextAlign.center)),
      ]));
  }
}
