import 'package:dio/dio.dart';
import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter/foundation.dart';
import '../callkit/callkit_service.dart';

const _apiBaseUrl = String.fromEnvironment(
  'API_URL',
  defaultValue: 'https://api.kitmunicator.intern.phudevelopement.xyz',
);

// Top-level Handler für Background-Messages (muss außerhalb jeder Klasse sein)
@pragma('vm:entry-point')
Future<void> _firebaseMessagingBackgroundHandler(RemoteMessage message) async {
  await Firebase.initializeApp();
  debugPrint('[FCM] Background-Nachricht: ${message.data}');
  await _handleCallPush(message);
}

Future<void> _handleCallPush(RemoteMessage message) async {
  final data = message.data;
  if (data['type'] != 'incoming_call') return;

  final uuid     = data['uuid']        ?? '';
  final callerId = data['caller_id']   ?? 'Unbekannt';
  final callerName = data['caller_name'] ?? callerId;

  await CallKitService.showIncomingFromPush(
    uuid: uuid,
    callerId: callerId,
    callerName: callerName,
  );
}

class PushService {
  PushService._();
  static final instance = PushService._();

  Future<void> init() async {
    FirebaseMessaging.onBackgroundMessage(_firebaseMessagingBackgroundHandler);

    // Berechtigung anfragen (Android 13+)
    final settings = await FirebaseMessaging.instance.requestPermission(
      alert: true,
      badge: true,
      sound: true,
    );
    debugPrint('[FCM] Berechtigung: ${settings.authorizationStatus}');

    // Foreground-Messages
    FirebaseMessaging.onMessage.listen((message) {
      debugPrint('[FCM] Foreground-Nachricht: ${message.data}');
      _handleCallPush(message);
    });

    // App aus terminated state via Notification geöffnet
    FirebaseMessaging.instance.getInitialMessage().then((message) {
      if (message != null) _handleCallPush(message);
    });

    // Token loggen (zum Testen)
    final token = await FirebaseMessaging.instance.getToken();
    debugPrint('[FCM] Token: $token');

    FirebaseMessaging.instance.onTokenRefresh.listen((newToken) {
      debugPrint('[FCM] Token erneuert: $newToken');
      // Wird bei nächstem Login automatisch neu registriert via registerTokenWithBackend()
    });
  }

  Future<String?> getToken() => FirebaseMessaging.instance.getToken();

  /// Sendet den aktuellen FCM-Token ans Backend (nach Login aufrufen).
  Future<void> registerTokenWithBackend(String accessToken) async {
    final token = await getToken();
    if (token == null) return;

    try {
      final dio = Dio(BaseOptions(
        baseUrl: _apiBaseUrl,
        headers: {
          'Authorization': 'Bearer $accessToken',
          'Content-Type': 'application/json',
        },
        sendTimeout: const Duration(seconds: 10),
        receiveTimeout: const Duration(seconds: 10),
      ));
      await dio.put('/telephony/push-token', data: {'token': token});
      debugPrint('[FCM] Token beim Backend registriert');
    } catch (e) {
      debugPrint('[FCM] Token-Registrierung fehlgeschlagen: $e');
    }
  }
}
