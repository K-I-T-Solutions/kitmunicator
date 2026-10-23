import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../api/api_client.dart';
import '../auth/auth_service.dart';

/// SIP-Zugangsdaten des angemeldeten Users — wie in der Web-App vom Backend,
/// nicht aus dem Keycloak-Namen (der SIP-Username kann davon abweichen).
class SipCredentials {
  final String username;
  final String extension;
  final String password;

  const SipCredentials({required this.username, required this.extension, required this.password});

  factory SipCredentials.fromJson(Map<String, dynamic> json) => SipCredentials(
        username: json['username'] as String,
        extension: json['extension'] as String,
        password: json['password'] as String,
      );
}

/// Lädt nur beim An-/Abmelden neu, nicht bei jedem Token-Refresh.
final sipCredentialsProvider = FutureProvider<SipCredentials?>((ref) async {
  final loggedIn = ref.watch(authProvider.select((a) => a.isAuthenticated));
  if (!loggedIn) return null;

  final res = await ref.read(apiClientProvider).get<Map<String, dynamic>>('/telephony/accounts/me/credentials');
  return SipCredentials.fromJson(res.data!);
});
