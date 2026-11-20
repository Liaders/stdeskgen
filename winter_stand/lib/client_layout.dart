import 'package:flutter/painting.dart';

/// Geometry from StatusDesk's RustDesk 1.5.1 desktop_home_page.dart and _Logo:
/// 200px sidebar, 60px logo box, 20/16px tip margins, 57px ID board.
/// Native bindings are deliberately absent; text is measured with the same styles.
class ClientSidebarLayout {
  static const width = 200.0;
  final List<(String, Offset, TextStyle)> labels = [];
  final List<(int, int)> bands = [];
  late final Rect logo, id, password, settings, refresh, edit;
  late final double idTop, passwordTop;
  ClientSidebarLayout() {
    const logoHeight = 60.0;
    const logoWidth = logoHeight * 1187 / 564;
    logo =
        const Rect.fromLTWH((width - logoWidth) / 2, 12, logoWidth, logoHeight);
    bands.add((12, 41));
    bands.add((41, 73));
    double label(String value, double x, double y, double fontSize,
        {double? height}) {
      final style =
          TextStyle(fontFamily: 'Roboto', fontSize: fontSize, height: height);
      final painter = TextPainter(
          text: TextSpan(text: value, style: style),
          textDirection: TextDirection.ltr)
        ..layout(maxWidth: width - 36);
      for (final line in painter.computeLineMetrics()) {
        final top = y + line.baseline - line.ascent;
        bands.add((top.floor(), (top + line.height).ceil()));
      }
      labels.add((value, Offset(x, y), style));
      final result = painter.height;
      painter.dispose();
      return result;
    }

    const titleTop = 12 + logoHeight + 16;
    final titleHeight = label('Ваш рабочий стол', 20, titleTop, 19);
    final tipTop = titleTop + titleHeight + 10;
    final tipHeight = label(
        'Ваш рабочий стол доступен с этим ID и паролем.', 20, tipTop, 12,
        height: 1.25);
    idTop = tipTop + tipHeight + 5;
    label('ID', 29, idTop + 5, 14);
    id = Rect.fromLTWH(29, idTop + 25, 160, 32);
    settings = Rect.fromLTWH(161, idTop, 28, 25);
    passwordTop = idTop + 57 + 13;
    label('Одноразовый пароль', 29, passwordTop, 14);
    password = Rect.fromLTWH(29, passwordTop + 18, 95, 38);
    refresh = Rect.fromLTWH(124, passwordTop + 21, 30, 30);
    edit = Rect.fromLTWH(154, passwordTop + 21, 30, 30);
  }
  List<Rect> get protectedAreas => [id, password, settings, refresh, edit];
}

// Upstream str2color: identical peer-thumbnail colours, no native calls.
Color clientPeerColor(String peerId) {
  final str = '${peerId.replaceAll(' ', '')}Windows';
  var hash = 160 << 16 + 114 << 8 + 91;
  for (var i = 0; i < str.length; i++) {
    hash = str.codeUnitAt(i) + ((hash << 5) - hash);
  }
  hash %= 16777216;
  return Color((hash & 0xFF7FFF) | (0x7f << 24));
}
