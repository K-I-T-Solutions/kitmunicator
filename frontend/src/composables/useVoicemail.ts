import { computed, ref } from 'vue'
import { useAuthStore } from '@/stores/auth'

export interface Voicemail {
  id: number
  caller_number: string
  caller_name: string | null
  duration_seconds: number
  is_read: boolean
  received_at: string
}

// Geteilter Zustand: Navigation zeigt die Zahl ungelesener Nachrichten
const messages = ref<Voicemail[]>([])
const loadState = ref<'idle' | 'loading' | 'ready' | 'error'>('idle')

const POLL_INTERVAL_MS = 60_000
let pollTimer: ReturnType<typeof setInterval> | null = null

export function useVoicemail() {
  const auth = useAuthStore()

  const unreadCount = computed(() => messages.value.filter(m => !m.is_read).length)

  async function load(): Promise<void> {
    if (loadState.value === 'idle') loadState.value = 'loading'
    try {
      const res = await fetch('/api/telephony/voicemail', { headers: auth.getAuthHeader() })
      if (!res.ok) throw new Error(String(res.status))
      messages.value = await res.json()
      loadState.value = 'ready'
    } catch {
      loadState.value = 'error'
    }
  }

  /** Neue Nachrichten kommen ohne Event — regelmäßig nachsehen */
  function startPolling(): void {
    if (pollTimer) return
    load()
    pollTimer = setInterval(load, POLL_INTERVAL_MS)
  }

  async function markRead(id: number): Promise<void> {
    const vm = messages.value.find(m => m.id === id)
    if (!vm || vm.is_read) return
    vm.is_read = true
    const res = await fetch(`/api/telephony/voicemail/${id}/read`, {
      method: 'PATCH',
      headers: auth.getAuthHeader(),
    })
    if (!res.ok) vm.is_read = false
  }

  /** Audio mit Bearer-Token laden — ein <audio src> könnte keinen Header senden */
  async function fetchAudio(id: number): Promise<string> {
    const res = await fetch(`/api/telephony/voicemail/${id}/audio`, { headers: auth.getAuthHeader() })
    if (!res.ok) throw new Error(String(res.status))
    return URL.createObjectURL(await res.blob())
  }

  return { messages, loadState, unreadCount, load, startPolling, markRead, fetchAudio }
}
