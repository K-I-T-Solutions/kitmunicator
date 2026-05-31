import { defineStore } from 'pinia'
import { ref, computed, shallowRef } from 'vue'
import {
  UserAgent,
  Registerer,
  Inviter,
  Invitation,
  Session,
  SessionState,
  type UserAgentOptions,
} from 'sip.js'
import { useAuthStore } from './auth'

export type CallState = 'idle' | 'registering' | 'registered' | 'calling' | 'incoming' | 'connected' | 'error'

export const usePhoneStore = defineStore('phone', () => {
  const callState = ref<CallState>('idle')
  const remoteNumber = ref<string | null>(null)
  const isMuted = ref(false)
  const isOnHold = ref(false)
  const callDurationSeconds = ref(0)
  const errorMessage = ref<string | null>(null)

  // shallowRef – SIP.js-Objekte sind nicht reaktiv-kompatibel
  const userAgent = shallowRef<UserAgent | null>(null)
  const registerer = shallowRef<Registerer | null>(null)
  const activeSession = shallowRef<Session | null>(null)

  let _durationTimer: ReturnType<typeof setInterval> | null = null

  // AudioContext statt HTMLAudioElement.
  // Muss im User-Gesture-Kontext (call/answer) entsperrt werden,
  // damit Chrome die Autoplay-Policy nicht blockiert.
  let _audioCtx: AudioContext | null = null
  let _sourceNode: MediaStreamAudioSourceNode | null = null

  const isRegistered = computed(() => callState.value === 'registered')
  const isBusy = computed(() => ['calling', 'incoming', 'connected'].includes(callState.value))

  // Wird in call() und answer() gerufen – direkt im Click-Handler = User-Gesture.
  // Chrome erlaubt Audio nur wenn AudioContext im User-Gesture-Kontext gestartet wurde.
  function _initAudioContext(): void {
    if (!_audioCtx) {
      _audioCtx = new AudioContext()
    }
    if (_audioCtx.state === 'suspended') {
      _audioCtx.resume().catch((err) => console.warn('[Phone] AudioContext.resume() fehlgeschlagen:', err))
    }
  }

  function _attachRemoteStream(session: Session): void {
    const pc = (session.sessionDescriptionHandler as { peerConnection?: RTCPeerConnection })?.peerConnection
    if (!pc) { console.warn('[Phone] _attachRemoteStream: kein PeerConnection'); return }

    console.log('[Phone] _attachRemoteStream – AudioCtx state:', _audioCtx?.state ?? 'null',
      '| receivers:', pc.getReceivers().length)

    const attach = (track: MediaStreamTrack | null) => {
      console.log('[Phone] attach track:', track?.kind ?? 'null', '| readyState:', track?.readyState)
      if (!track || track.kind !== 'audio') return
      if (!_audioCtx) {
        console.warn('[Phone] AudioContext nicht initialisiert – Audio nicht möglich')
        errorMessage.value = 'Audio-Kontext nicht bereit. Bitte neu anrufen.'
        return
      }
      try {
        _sourceNode?.disconnect()
        _sourceNode = _audioCtx.createMediaStreamSource(new MediaStream([track]))
        _sourceNode.connect(_audioCtx.destination)
        console.log('[Phone] AudioContext source verbunden – Audio sollte spielen')
      } catch (err) {
        console.error('[Phone] AudioContext Fehler:', err)
        errorMessage.value = 'Audio-Fehler: ' + String(err)
      }
    }

    // Tracks die schon da sind (ontrack bereits gefeuert) sofort anhängen
    for (const receiver of pc.getReceivers()) {
      attach(receiver.track)
    }

    // Alle künftigen Tracks
    pc.addEventListener('track', (event: RTCTrackEvent) => {
      console.log('[Phone] ontrack event – streams:', event.streams.length)
      attach(event.track)
    })
  }

  function _startDurationTimer(): void {
    callDurationSeconds.value = 0
    _durationTimer = setInterval(() => { callDurationSeconds.value++ }, 1000)
  }

  function _stopDurationTimer(): void {
    if (_durationTimer) { clearInterval(_durationTimer); _durationTimer = null }
    callDurationSeconds.value = 0
  }

  function _onSessionStateChange(state: SessionState, session: Session): void {
    switch (state) {
      case SessionState.Establishing:
        callState.value = 'calling'
        break
      case SessionState.Established:
        callState.value = 'connected'
        _attachRemoteStream(session)
        _startDurationTimer()
        break
      case SessionState.Terminated:
        callState.value = 'registered'
        remoteNumber.value = null
        isMuted.value = false
        isOnHold.value = false
        activeSession.value = null
        _sourceNode?.disconnect()
        _sourceNode = null
        _stopDurationTimer()
        break
    }
  }

  async function setup(sipUri: string, password: string, wsServer: string): Promise<void> {
    if (userAgent.value) return

    const auth = useAuthStore()

    const options: UserAgentOptions = {
      uri: UserAgent.makeURI(sipUri),
      transportOptions: { server: wsServer },
      authorizationUsername: sipUri.split(':')[1]?.split('@')[0] ?? '',
      authorizationPassword: password,
      displayName: auth.displayName,
      sessionDescriptionHandlerFactoryOptions: {
        peerConnectionConfiguration: {
          iceServers: [
            { urls: `stun:${import.meta.env.VITE_TURN_HOST}:3478` },
          ],
        },
      },
      delegate: {
        onInvite(invitation: Invitation) {
          activeSession.value = invitation
          remoteNumber.value = invitation.remoteIdentity.uri.user ?? 'Unbekannt'
          callState.value = 'incoming'
          invitation.stateChange.addListener((state) => _onSessionStateChange(state, invitation))
        },
      },
    }

    const ua = new UserAgent(options)
    userAgent.value = ua
    callState.value = 'registering'

    const reg = new Registerer(ua)
    registerer.value = reg

    reg.stateChange.addListener((state) => {
      if (state === 'Registered') callState.value = 'registered'
      else if (state === 'Unregistered') callState.value = 'idle'
    })

    await ua.start()
    await reg.register()
  }

  // 169.254.x.x Link-Local aus dem SDP entfernen/ersetzen –
  // Asterisk im Docker-Netz kann diese Adressen nicht erreichen.
  // Betrifft: c= Verbindungszeile UND a=candidate:-Einträge.
  function _stripLinkLocal(description: RTCSessionDescriptionInit): Promise<RTCSessionDescriptionInit> {
    const filtered = (description.sdp ?? '')
      .split('\n')
      .map(line => line.startsWith('c=IN IP4 169.254.') ? 'c=IN IP4 0.0.0.0' : line)
      .filter(line => !(line.startsWith('a=candidate:') && line.includes(' 169.254.')))
      .join('\n')
    return Promise.resolve({ ...description, sdp: filtered })
  }

  async function call(target: string): Promise<void> {
    if (!userAgent.value || !isRegistered.value) return
    const targetUri = UserAgent.makeURI(`sip:${target}@${import.meta.env.VITE_SIP_DOMAIN}`)
    if (!targetUri) return

    // AudioContext im User-Gesture-Kontext entsperren (Chrome Autoplay-Policy)
    _initAudioContext()

    const inviter = new Inviter(userAgent.value, targetUri)
    activeSession.value = inviter
    remoteNumber.value = target
    callState.value = 'calling'

    inviter.stateChange.addListener((state) => _onSessionStateChange(state, inviter))
    try {
      await inviter.invite({
        sessionDescriptionHandlerModifiers: [_stripLinkLocal],
      })
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err)
      console.error('[Phone] invite() fehlgeschlagen:', msg)
      const isPermission = /notallowed|permission denied/i.test(msg)
      errorMessage.value = isPermission
        ? 'Mikrofon-Zugriff verweigert – bitte in den Browser-Einstellungen erlauben.'
        : `Anruf fehlgeschlagen: ${msg}`
      callState.value = 'registered'
      activeSession.value = null
      remoteNumber.value = null
    }
  }

  async function hangup(): Promise<void> {
    if (!activeSession.value) return
    const session = activeSession.value
    if (session instanceof Inviter) {
      await session.cancel().catch(() => session.bye())
    } else if (session instanceof Invitation) {
      if (session.state === SessionState.Established) await session.bye()
      else await session.reject()
    }
  }

  async function answer(): Promise<void> {
    if (!(activeSession.value instanceof Invitation)) return
    // AudioContext im User-Gesture-Kontext entsperren (Chrome Autoplay-Policy)
    _initAudioContext()
    try {
      await activeSession.value.accept()
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err)
      console.error('[Phone] accept() fehlgeschlagen:', msg)
      const isPermission = /notallowed|permission denied/i.test(msg)
      errorMessage.value = isPermission
        ? 'Mikrofon-Zugriff verweigert – bitte in den Browser-Einstellungen erlauben.'
        : `Anruf konnte nicht angenommen werden: ${msg}`
    }
  }

  async function toggleMute(): Promise<void> {
    const session = activeSession.value
    if (!session) return
    const pc = (session.sessionDescriptionHandler as { peerConnection?: RTCPeerConnection })?.peerConnection
    if (!pc) return
    pc.getSenders().forEach((sender) => {
      if (sender.track?.kind === 'audio') sender.track.enabled = isMuted.value
    })
    isMuted.value = !isMuted.value
  }

  async function toggleHold(): Promise<void> {
    if (!activeSession.value) return
    if (isOnHold.value) {
      await (activeSession.value as Inviter & { unhold?: () => Promise<void> }).unhold?.()
    } else {
      await (activeSession.value as Inviter & { hold?: () => Promise<void> }).hold?.()
    }
    isOnHold.value = !isOnHold.value
  }

  return {
    callState,
    remoteNumber,
    isMuted,
    isOnHold,
    callDurationSeconds,
    errorMessage,
    isRegistered,
    isBusy,
    setup,
    call,
    hangup,
    answer,
    toggleMute,
    toggleHold,
  }
})
