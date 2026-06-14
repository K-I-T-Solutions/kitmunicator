import { usePhoneStore } from '@/stores/phone'
import { useAuthStore } from '@/stores/auth'
import { storeToRefs } from 'pinia'

export function usePhone() {
  const store = usePhoneStore()
  const auth = useAuthStore()

  const {
    callState,
    remoteNumber,
    isMuted,
    isOnHold,
    callDurationSeconds,
    errorMessage,
    isRegistered,
    isBusy,
  } = storeToRefs(store)

  async function register(): Promise<void> {
    const res = await fetch('/api/telephony/accounts/me/credentials', {
      headers: auth.getAuthHeader(),
    })
    if (!res.ok) {
      console.error('Kein SIP-Account gefunden – Registrierung übersprungen')
      return
    }
    const { username, password } = await res.json() as { username: string; extension: string; password: string }
    const sipUri = `sip:${username}@${import.meta.env.VITE_SIP_DOMAIN}`
    const wsServer = import.meta.env.VITE_SIP_WS_SERVER

    await store.setup(sipUri, password, wsServer)
  }

  async function call(target: string): Promise<void> {
    if (!isRegistered.value) await register()
    await store.call(target)
  }

  function hangup(): Promise<void> {
    return store.hangup()
  }

  function answer(): Promise<void> {
    return store.answer()
  }

  function mute(): Promise<void> {
    return store.toggleMute()
  }

  function hold(): Promise<void> {
    return store.toggleHold()
  }

  // Dauer formatiert als MM:SS
  function formatDuration(seconds: number): string {
    const m = Math.floor(seconds / 60).toString().padStart(2, '0')
    const s = (seconds % 60).toString().padStart(2, '0')
    return `${m}:${s}`
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
    formatDuration,
    register,
    call,
    hangup,
    answer,
    mute,
    hold,
  }
}
