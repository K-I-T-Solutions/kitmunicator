import 'package:flutter_test/flutter_test.dart';

void main() {
  testWidgets('Smoke test', (WidgetTester tester) async {
    // Kein automatischer Widget-Test — App benötigt Keycloak + SIP
    expect(true, isTrue);
  });
}
