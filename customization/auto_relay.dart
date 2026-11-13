class RdgenAutoRelayRetry {
  bool tried = false;
  bool pending = false;

  static bool isNetworkError(String message) {
    final text = message.toLowerCase();
    if (['password', 'permission', 'denied', 'authentication', 'rejected',
         'offline', 'not exist', 'blocked', 'not allowed'].any(text.contains)) return false;
    return ['reset by the peer', 'connection reset', 'timed out', 'timeout',
            'deadline', 'connection refused', 'network is unreachable',
            'no route to host', 'connection aborted', 'broken pipe'].any(text.contains);
  }

  bool begin(String message) {
    if (tried || !isNetworkError(message)) return false;
    tried = true;
    pending = true;
    return true;
  }

  bool authenticated({required bool relayed}) {
    final remember = pending && relayed;
    pending = false;
    return remember;
  }

  void reset() { tried = false; pending = false; }
}
