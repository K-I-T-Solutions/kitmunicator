import 'dart:async';
import 'package:flutter/foundation.dart';
import 'package:sip_ua/sip_ua.dart' as sip;
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../callkit/callkit_service.dart';

enum PhoneState { idle, registering, registered, calling, incoming, connected, error }

class SipState {
  final PhoneState callState;
  final String? remoteNumber;
  final bool isMuted;
  final String? errorMessage;

  const SipState({
    this.callState = PhoneState.idle,
    this.remoteNumber,
    this.isMuted = false,
    this.errorMessage,
  });

  bool get isRegistered => callState == PhoneState.registered;

  SipState copyWith({
    PhoneState? callState,
    String? remoteNumber,
    bool? isMuted,
    String? errorMessage,
  }) => SipState(
    callState: callState ?? this.callState,
    remoteNumber: remoteNumber,
    isMuted: isMuted ?? this.isMuted,
    errorMessage: errorMessage,
  );
}

class SipNotifier extends StateNotifier<SipState> implements sip.SipUaHelperListener {
  SipNotifier() : super(const SipState()) {
    _subscribeCallKit();
  }

  sip.SIPUAHelper? _helper;
  sip.Call? _activeCall;
  StreamSubscription<CallKitEvent>? _callKitSub;
  // Wenn CallKit "Annehmen" gedrückt wird bevor das SIP-INVITE ankommt
  bool _pendingAnswer = false;

  void _subscribeCallKit() {
    _callKitSub = CallKitService.instance.events.listen((event) {
      switch (event) {
        case CallKitEvent.accepted:
          answer();
        case CallKitEvent.declined:
        case CallKitEvent.timeout:
        case CallKitEvent.ended:
          hangup();
      }
    });
  }

  Future<void> setup({
    required String sipUri,
    required String password,
    required String wsServer,
    required String displayName,
  }) async {
    if (_helper != null) return;

    CallKitService.instance.init();

    _helper = sip.SIPUAHelper();
    _helper!.addSipUaHelperListener(this);

    final settings = sip.UaSettings()
      ..transportType     = sip.TransportType.WS
      ..webSocketUrl      = wsServer
      ..uri               = sipUri
      ..authorizationUser = sipUri.split(':').length > 1
          ? sipUri.split(':')[1].split('@')[0]
          : ''
      ..password          = password
      ..displayName       = displayName
      ..userAgent         = 'KITmunicator-Flutter/1.0'
      ..iceServers        = [
          {'url': 'stun:${const String.fromEnvironment('TURN_HOST', defaultValue: '192.168.178.100')}:3478'},
        ];

    state = state.copyWith(callState: PhoneState.registering);
    await _helper!.start(settings);
  }

  Future<void> call(String target) async {
    if (_helper == null || !state.isRegistered) return;
    final domain = const String.fromEnvironment(
      'SIP_DOMAIN',
      defaultValue: 'kitmunicator.intern.phudevelopement.xyz',
    );
    state = state.copyWith(callState: PhoneState.calling, remoteNumber: target);
    await _helper!.call('sip:$target@$domain', voiceOnly: true);
  }

  void answer() {
    if (_helper == null) return;
    if (_activeCall == null) {
      // INVITE noch nicht angekommen — merken und beim nächsten INVITE auto-answern
      _pendingAnswer = true;
      return;
    }
    _pendingAnswer = false;
    _activeCall!.answer(_helper!.buildCallOptions(true));
  }

  void hangup() {
    _pendingAnswer = false;
    if (_activeCall == null) return;
    try {
      _activeCall!.hangup();
    } catch (_) {}
    CallKitService.instance.endCall();
  }

  void toggleMute() {
    if (_activeCall == null) return;
    if (state.isMuted) {
      _activeCall!.unmute(true, false);
    } else {
      _activeCall!.mute(true, false);
    }
    state = state.copyWith(isMuted: !state.isMuted);
  }

  @override
  void dispose() {
    _callKitSub?.cancel();
    super.dispose();
  }

  // ── SipUaHelperListener ────────────────────────────────────────────────────

  @override
  void registrationStateChanged(sip.RegistrationState s) {
    switch (s.state) {
      case sip.RegistrationStateEnum.REGISTERED:
        state = state.copyWith(callState: PhoneState.registered);
      case sip.RegistrationStateEnum.UNREGISTERED:
      case sip.RegistrationStateEnum.REGISTRATION_FAILED:
        state = state.copyWith(callState: PhoneState.idle);
      default:
        break;
    }
  }

  @override
  void callStateChanged(sip.Call call, sip.CallState callState) {
    _activeCall = call;
    debugPrint('[SIP] callStateChanged: state=${callState.state} direction=${call.direction}');
    switch (callState.state) {
      case sip.CallStateEnum.CALL_INITIATION:
        final isIncoming = call.direction == 'INCOMING';
        if (isIncoming) {
          final from = call.remote_identity ?? 'Unbekannt';
          state = state.copyWith(callState: PhoneState.incoming, remoteNumber: from);
          if (_pendingAnswer) {
            // User hat schon über CallKit-Push angenommen → direkt durchschalten
            _pendingAnswer = false;
            Future.microtask(() => answer());
          } else {
            CallKitService.instance.showIncoming(callerId: from, callerName: from);
          }
        } else {
          state = state.copyWith(callState: PhoneState.calling);
        }
      case sip.CallStateEnum.ACCEPTED:
      case sip.CallStateEnum.CONFIRMED:
        state = state.copyWith(callState: PhoneState.connected);
      case sip.CallStateEnum.FAILED:
      case sip.CallStateEnum.ENDED:
        _activeCall = null;
        state = state.copyWith(
          callState: PhoneState.registered,
          remoteNumber: null,
          isMuted: false,
        );
        CallKitService.instance.endCall();
      case sip.CallStateEnum.PROGRESS:
        break;
      default:
        break;
    }
  }

  @override
  void transportStateChanged(sip.TransportState s) {}

  @override
  void onNewMessage(sip.SIPMessageRequest msg) {}

  @override
  void onNewNotify(sip.Notify ntf) {}

  @override
  void onNewReinvite(sip.ReInvite event) {}
}

final sipProvider = StateNotifierProvider<SipNotifier, SipState>(
  (_) => SipNotifier(),
);
