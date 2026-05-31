import 'dart:async';
import 'package:flutter_callkit_incoming/flutter_callkit_incoming.dart';
import 'package:flutter_callkit_incoming/entities/entities.dart';
import 'package:uuid/uuid.dart';

enum CallKitEvent { accepted, declined, ended, timeout }

class CallKitService {
  CallKitService._();
  static final instance = CallKitService._();

  final _events = StreamController<CallKitEvent>.broadcast();
  Stream<CallKitEvent> get events => _events.stream;

  String? _activeUuid;

  void init() {
    FlutterCallkitIncoming.onEvent.listen((event) {
      switch (event?.event) {
        case Event.actionCallAccept:
          _events.add(CallKitEvent.accepted);
        case Event.actionCallDecline:
          _events.add(CallKitEvent.declined);
        case Event.actionCallEnded:
          _events.add(CallKitEvent.ended);
        case Event.actionCallTimeout:
          _events.add(CallKitEvent.timeout);
        default:
          break;
      }
    });
  }

  Future<void> showIncoming({
    required String callerId,
    required String callerName,
  }) async {
    _activeUuid = const Uuid().v4();

    await FlutterCallkitIncoming.showCallkitIncoming(CallKitParams(
      id: _activeUuid!,
      nameCaller: callerName,
      appName: 'KITmunicator',
      type: 0,
      duration: 30000,
      textAccept: 'Annehmen',
      textDecline: 'Ablehnen',
      android: const AndroidParams(
        isCustomNotification: false,
        isShowLogo: false,
        isShowFullLockedScreen: true,
        backgroundColor: '#0A1628',
        actionColor: '#06B6D4',
        incomingCallNotificationChannelName: 'Eingehender Anruf',
        missedCallNotificationChannelName: 'Verpasster Anruf',
      ),
      ios: const IOSParams(
        handleType: 'number',
        supportsVideo: false,
        maximumCallGroups: 1,
        maximumCallsPerCallGroup: 1,
        audioSessionMode: 'default',
        audioSessionActive: true,
        audioSessionPreferredSampleRate: 44100.0,
        audioSessionPreferredIOBufferDuration: 0.005,
        supportsDTMF: true,
        supportsHolding: false,
        supportsGrouping: false,
        supportsUngrouping: false,
        ringtonePath: 'system_ringtone_default',
      ),
    ));
  }

  Future<void> endCall() async {
    if (_activeUuid == null) return;
    await FlutterCallkitIncoming.endCall(_activeUuid!);
    _activeUuid = null;
  }

  Future<void> endAllCalls() async {
    await FlutterCallkitIncoming.endAllCalls();
    _activeUuid = null;
  }

  static Future<void> showIncomingFromPush({
    required String uuid,
    required String callerId,
    required String callerName,
  }) async {
    await FlutterCallkitIncoming.showCallkitIncoming(CallKitParams(
      id: uuid,
      nameCaller: callerName,
      appName: 'KITmunicator',
      type: 0,
      duration: 30000,
      textAccept: 'Annehmen',
      textDecline: 'Ablehnen',
      android: const AndroidParams(
        isCustomNotification: false,
        isShowLogo: false,
        isShowFullLockedScreen: true,
        backgroundColor: '#0A1628',
        actionColor: '#06B6D4',
        incomingCallNotificationChannelName: 'Eingehender Anruf',
        missedCallNotificationChannelName: 'Verpasster Anruf',
      ),
      ios: const IOSParams(
        handleType: 'number',
        supportsVideo: false,
        supportsDTMF: true,
      ),
    ));
  }
}
