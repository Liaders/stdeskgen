import 'package:flutter_test/flutter_test.dart';
import 'package:statusdesk_winter_lab/main.dart';

void main() {
  testWidgets('winter lab opens without starting snow', (tester) async {
    await tester.pumpWidget(const WinterLab());
    expect(find.text('Кадры без рисования'), findsOneWidget);
    expect(find.byType(SnowLayer), findsNothing);
    expect(tester.takeException(), isNull);
  });
}
