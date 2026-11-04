import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_hbb/models/rdgen_device_display_name.dart';

void main() {
  test('Server alias takes priority over local alias and hostname', () {
    expect(resolveDeviceName(serverAlias: 'Reception', localAlias: 'Office',
        hostname: 'DESKTOP-123', id: '123'), 'Reception');
  });

  test('Missing or cleared server alias restores local name', () {
    for (final serverAlias in ['', '   ']) {
      expect(resolveDeviceName(serverAlias: serverAlias, localAlias: 'Office',
          hostname: 'DESKTOP-123', id: '123'), 'Office');
    }
  });

  test('Empty names fall back to hostname then ID', () {
    expect(resolveDeviceName(serverAlias: '', localAlias: '',
        hostname: 'DESKTOP-123', id: '123'), 'DESKTOP-123');
    expect(resolveDeviceName(serverAlias: '', localAlias: ' ',
        hostname: '', id: '123'), '123');
  });
}
