"""Copy the production shell; replace icon rendering only in the stand copy."""
from pathlib import Path
root = Path(__file__).resolve().parent
source = (root.parent/'customization/compact_session_toolbar.dart').read_text(encoding='utf-8')
if source.count('class RdgenToolbarGlyph extends StatelessWidget') != 1:
    raise SystemExit('Production toolbar glyph anchor changed; update the stand adapter.')
source = source.replace("import 'dart:math' as math;", "import 'dart:math' as math;" + chr(10) + "import '../stand_icons.dart';")
source = source.replace('class RdgenToolbarGlyph extends StatelessWidget', 'class RdgenOriginalToolbarGlyph extends StatelessWidget')
source = source.replace('const RdgenToolbarGlyph(this.kind,', 'const RdgenOriginalToolbarGlyph(this.kind,')
source += """
class RdgenToolbarGlyph extends StatelessWidget {
  final String kind;
  final Color? color;
  const RdgenToolbarGlyph(this.kind, {super.key, this.color});
  @override
  Widget build(BuildContext context) => StandToolbarIcon(kind,
    color: color ?? rdgenToolbarForeground(context),
    fallback: RdgenOriginalToolbarGlyph(kind, color: color));
}
"""
destination = root/'lib/models/rdgen_compact_session_toolbar.dart'
destination.parent.mkdir(parents=True, exist_ok=True)
destination.write_text(source, encoding='utf-8')
