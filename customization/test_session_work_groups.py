import io
import os
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile
import unittest

from session_work_groups import apply
from session_titles import apply as apply_titles
from desktop_ui import apply as apply_desktop
from apply_profile import apply as apply_profile


class SessionWorkGroupTests(unittest.TestCase):
    def test_hooks_preserve_connection_path_and_coexist_with_customizations(self):
        source = Path(__file__).resolve().parents[2]/'rustdesk'
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            data = subprocess.check_output(['git', '-c', f'safe.directory={source.as_posix()}',
                '-C', str(source), 'archive', os.environ.get('RUSTDESK_TEST_REF', 'HEAD'),
                'flutter/lib', 'src/lang'])
            with tarfile.open(fileobj=io.BytesIO(data)) as archive:
                archive.extractall(root, filter='data')
            path = root/'flutter/lib/models/model.dart'
            original = path.read_text(encoding='utf-8')
            apply(root)
            text = path.read_text(encoding='utf-8')
            original_query = original[original.index('  void _queryAuditGuid('):original.index('  /// Handle the peer info')]
            self.assertIn(original_query, text)  # Notes retain their existing independent path.
            self.assertIn('final workGroup = isCache ? null', text)
            self.assertIn('sessionGetConnSessionId(sessionId: sessionId)', text)
            self.assertNotIn('mainSetLocalOption', text[text.index('  String? _rdgen'):text.index('  void _queryAuditGuid')])
            apply_titles(root)
            apply_desktop(root, {'slim_ui': True})
            apply_profile(root, '1.5.1', {'schema_version': 1, 'device_names': True, 'colleagues': True, 'organizations': True})
            self.assertIn('preferredGroupId: rdgenPreferredWorkGroupId', text)
            self.assertIn('("Confirm", "Подтвердить")', (root/'src/lang/ru.rs').read_text(encoding='utf-8'))
            self.assertIn('dismissAllExceptTag', text)
            # Every desktop session type carries the hint through initial and reused windows.
            for kind in ['remote', 'file_manager', 'view_camera', 'port_forward', 'terminal']:
                tab = (root/f'flutter/lib/desktop/pages/{kind}_tab_page.dart').read_text(encoding='utf-8')
                self.assertIn("rdgenWorkGroupId: params['rdgen_work_group_id']", tab)
                self.assertIn("rdgenWorkGroupId: args['rdgen_work_group_id']", tab)
            if shutil.which('dart'):
                files = [path, root/'flutter/lib/common.dart', root/'flutter/lib/utils/multi_window_manager.dart',
                         *path.parent.glob('rdgen_*.dart')]
                files += [p for p in (root/'flutter/lib/desktop/pages').glob('*.dart')
                          if 'rdgenWorkGroupId' in p.read_text(encoding='utf-8')]
                for file in files:
                    subprocess.run(['dart', 'format', '--output=none', str(file)], check=True, capture_output=True, timeout=60)

    @unittest.skipUnless(shutil.which('dart'), 'Dart SDK is available on CI')
    def test_exact_session_protocol(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for src, dst in [('session_work_groups.dart', 'rdgen_session_work_groups.dart'),
                             ('organization_catalog.dart', 'rdgen_organization_catalog.dart'),
                             ('session_work_groups_test.dart', 'test.dart')]:
                shutil.copyfile(Path(__file__).with_name(src), root/dst)
            subprocess.run(['dart', str(root/'test.dart')], check=True, timeout=60)

    @unittest.skipUnless(shutil.which('flutter'), 'Flutter SDK is available on the widget runner')
    def test_picker_widgets(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root/'lib/models').mkdir(parents=True)
            (root/'test').mkdir()
            for name in ['session_work_groups', 'session_work_groups_ui', 'work_group_origin']:
                shutil.copyfile(Path(__file__).with_name(name+'.dart'), root/f'lib/models/rdgen_{name}.dart')
            shutil.copyfile(Path(__file__).with_name('session_work_groups_widget_test.dart'), root/'test/picker_test.dart')
            (root/'pubspec.yaml').write_text('name: session_work_groups_test\nenvironment:\n  sdk: ">=3.5.0 <4.0.0"\ndependencies:\n  flutter:\n    sdk: flutter\ndev_dependencies:\n  flutter_test:\n    sdk: flutter\n', encoding='utf-8')
            # Host only: same public signatures as common.dart, without unrelated FFI plugins.
            (root/'lib/common.dart').write_text('''import 'package:flutter/material.dart';
export 'package:flutter/material.dart';
String translate(String value) => value;
typedef CustomAlertDialog = AlertDialog;
class OverlayDialogManager {
  final BuildContext context;
  OverlayDialogManager(this.context);
  Future<T?> show<T>(AlertDialog Function(StateSetter, void Function([dynamic]), BuildContext) builder,
      {String? tag, bool backDismiss = false}) => showDialog<T>(context: context,
        builder: (context) => StatefulBuilder(builder: (context, setState) =>
          builder(setState, ([result]) => Navigator.of(context).pop(result), context)));
}
'''.replace('typedef CustomAlertDialog = AlertDialog;', '''class CustomAlertDialog extends AlertDialog {
  final VoidCallback? onCancel;
  CustomAlertDialog({super.title, required super.content, super.actions, this.onCancel});
}'''), encoding='utf-8')
            subprocess.run(['flutter', 'pub', 'get'], cwd=root, check=True, timeout=180)
            subprocess.run(['flutter', 'test'], cwd=root, check=True, timeout=180)
