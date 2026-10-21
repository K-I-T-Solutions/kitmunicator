import { ref } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { toGreetingWav } from '@/lib/wav'

export interface GreetingStatus {
  exists: boolean
  duration_seconds: number | null
  updated_at: string | null
}

export const GREETING_MAX_SECONDS = 60

/** Eigene Voicemail-Ansage: aufnehmen bzw. hochladen, prüfen, speichern */
export function useGreeting() {
  const auth = useAuthStore()

  const status = ref<GreetingStatus | null>(null)
  const recording = ref(false)
  const recordSeconds = ref(0)
  /** Fertig umgewandelt, noch nicht gespeichert */
  const draft = ref<{ wav: Blob; url: string; seconds: number } | null>(null)
  const busy = ref(false)
  const error = ref<string | null>(null)

  let recorder: MediaRecorder | null = null
  let stream: MediaStream | null = null
  let tick: ReturnType<typeof setInterval> | null = null

  async function load() {
    try {
      const res = await fetch('/api/telephony/greeting', { headers: auth.getAuthHeader() })
      if (!res.ok) throw new Error(String(res.status))
      status.value = await res.json()
    } catch {
      error.value = 'Ansage konnte nicht geladen werden.'
    }
  }

  function discardDraft() {
    if (draft.value) URL.revokeObjectURL(draft.value.url)
    draft.value = null
  }

  async function useAudio(blob: Blob) {
    error.value = null
    busy.value = true
    try {
      const { wav, seconds } = await toGreetingWav(blob)
      if (seconds < 1) throw new Error('Die Ansage ist zu kurz.')
      if (seconds > GREETING_MAX_SECONDS) throw new Error(`Die Ansage darf höchstens ${GREETING_MAX_SECONDS} Sekunden lang sein.`)
      discardDraft()
      draft.value = { wav, url: URL.createObjectURL(wav), seconds }
    } catch (err) {
      error.value = err instanceof Error && err.message.startsWith('Die Ansage')
        ? err.message
        : 'Die Datei konnte nicht gelesen werden.'
    } finally {
      busy.value = false
    }
  }

  async function startRecording() {
    error.value = null
    discardDraft()
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true } })
    } catch {
      error.value = 'Kein Zugriff aufs Mikrofon.'
      return
    }
    const chunks: Blob[] = []
    recorder = new MediaRecorder(stream)
    recorder.ondataavailable = e => chunks.push(e.data)
    recorder.onstop = () => {
      stream?.getTracks().forEach(t => t.stop())
      stream = null
      useAudio(new Blob(chunks, { type: recorder?.mimeType }))
    }
    recorder.start()
    recording.value = true
    recordSeconds.value = 0
    tick = setInterval(() => {
      recordSeconds.value++
      if (recordSeconds.value >= GREETING_MAX_SECONDS) stopRecording()
    }, 1000)
  }

  function stopRecording() {
    if (tick) { clearInterval(tick); tick = null }
    if (recorder?.state === 'recording') recorder.stop()
    recording.value = false
  }

  async function save() {
    if (!draft.value) return
    busy.value = true
    error.value = null
    try {
      const res = await fetch('/api/telephony/greeting', {
        method: 'PUT',
        headers: { ...auth.getAuthHeader(), 'Content-Type': 'audio/wav' },
        body: draft.value.wav,
      })
      if (!res.ok) {
        const body = await res.json().catch(() => null)
        throw new Error(body?.detail ?? String(res.status))
      }
      status.value = await res.json()
      discardDraft()
    } catch (err) {
      error.value = `Speichern fehlgeschlagen: ${err instanceof Error ? err.message : err}`
    } finally {
      busy.value = false
    }
  }

  async function remove() {
    busy.value = true
    error.value = null
    try {
      const res = await fetch('/api/telephony/greeting', { method: 'DELETE', headers: auth.getAuthHeader() })
      if (!res.ok) throw new Error(String(res.status))
      status.value = { exists: false, duration_seconds: null, updated_at: null }
    } catch {
      error.value = 'Löschen fehlgeschlagen.'
    } finally {
      busy.value = false
    }
  }

  /** Gespeicherte Ansage als Blob-URL (Audio braucht den Bearer-Header) */
  async function fetchSavedUrl(): Promise<string> {
    const res = await fetch('/api/telephony/greeting/audio', { headers: auth.getAuthHeader() })
    if (!res.ok) throw new Error(String(res.status))
    return URL.createObjectURL(await res.blob())
  }

  function dispose() {
    stopRecording()
    stream?.getTracks().forEach(t => t.stop())
    discardDraft()
  }

  return {
    status, recording, recordSeconds, draft, busy, error,
    load, startRecording, stopRecording, useAudio, save, remove, discardDraft, fetchSavedUrl, dispose,
  }
}
