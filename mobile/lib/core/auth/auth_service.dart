import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:flutter_appauth/flutter_appauth.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import '../push/push_service.dart';

const _storage   = FlutterSecureStorage();
const _appAuth   = FlutterAppAuth();

const _issuer      = String.fromEnvironment('KEYCLOAK_ISSUER',    defaultValue: 'https://login.intern.phudevelopement.xyz/realms/kit');
const _clientId    = String.fromEnvironment('KEYCLOAK_CLIENT_ID', defaultValue: 'kitmunicator');
const _redirectUri = 'de.kititkoblenz.kitmunicator://callback';
const _scopes      = ['openid', 'profile', 'email', 'offline_access'];

class AuthState {
  final String? accessToken;
  final String? displayName;
  final String? userId;
  final String? username;
  final bool isLoading;
  final String? error;

  const AuthState({
    this.accessToken,
    this.displayName,
    this.userId,
    this.username,
    this.isLoading = false,
    this.error,
  });

  bool get isAuthenticated => accessToken != null;

  AuthState copyWith({
    String? accessToken,
    String? displayName,
    String? userId,
    String? username,
    bool? isLoading,
    String? error,
  }) => AuthState(
    accessToken: accessToken ?? this.accessToken,
    displayName: displayName ?? this.displayName,
    userId: userId ?? this.userId,
    username: username ?? this.username,
    isLoading: isLoading ?? this.isLoading,
    error: error,
  );
}

class AuthNotifier extends StateNotifier<AuthState> {
  AuthNotifier() : super(const AuthState()) {
    _tryRestoreSession();
  }

  Future<void> _tryRestoreSession() async {
    final refreshToken = await _storage.read(key: 'refresh_token');
    if (refreshToken == null) return;
    try {
      await _refresh(refreshToken);
    } catch (_) {
      await _storage.deleteAll();
    }
  }

  Future<void> login() async {
    state = state.copyWith(isLoading: true, error: null);
    try {
      debugPrint('[AUTH] login() gestartet — issuer=$_issuer clientId=$_clientId redirectUri=$_redirectUri');
      final result = await _appAuth.authorizeAndExchangeCode(
        AuthorizationTokenRequest(
          _clientId,
          _redirectUri,
          issuer: _issuer,
          scopes: _scopes,
        ),
      );
      debugPrint('[AUTH] authorizeAndExchangeCode fertig — result=${result != null}');
      if (result == null) throw Exception('Login abgebrochen');
      await _applyTokens(result.accessToken, result.refreshToken, result.idToken);
    } catch (e) {
      debugPrint('[AUTH] Fehler: $e');
      state = state.copyWith(isLoading: false, error: e.toString());
    }
  }

  Future<void> _refresh(String refreshToken) async {
    final result = await _appAuth.token(
      TokenRequest(
        _clientId,
        _redirectUri,
        issuer: _issuer,
        refreshToken: refreshToken,
        scopes: _scopes,
      ),
    );
    if (result?.accessToken == null) throw Exception('Token-Refresh fehlgeschlagen');
    await _applyTokens(result!.accessToken, result.refreshToken, result.idToken);
  }

  Future<void> _applyTokens(String? access, String? refresh, String? idToken) async {
    if (access == null) return;
    if (refresh != null) await _storage.write(key: 'refresh_token', value: refresh);

    final claims  = _decodeJwtPayload(idToken);
    final name    = claims?['name'] as String?
                 ?? claims?['preferred_username'] as String?
                 ?? 'Benutzer';
    final sub     = claims?['sub'] as String? ?? '';
    final uname   = claims?['preferred_username'] as String? ?? sub;

    state = state.copyWith(
      accessToken: access,
      displayName: name,
      userId: sub,
      username: uname,
      isLoading: false,
    );

    // FCM-Token im Hintergrund ans Backend melden
    PushService.instance.registerTokenWithBackend(access);
  }

  Future<void> logout() async {
    await _storage.deleteAll();
    state = const AuthState();
  }

  Map<String, dynamic>? _decodeJwtPayload(String? token) {
    if (token == null) return null;
    try {
      final parts = token.split('.');
      if (parts.length < 2) return null;
      final normalized = base64Url.normalize(parts[1]);
      final payload    = utf8.decode(base64Url.decode(normalized));
      return jsonDecode(payload) as Map<String, dynamic>;
    } catch (_) {
      return null;
    }
  }
}

final authProvider = StateNotifierProvider<AuthNotifier, AuthState>(
  (_) => AuthNotifier(),
);
