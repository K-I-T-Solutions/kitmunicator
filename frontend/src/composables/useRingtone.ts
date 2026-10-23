import { ref, watch } from 'vue'
import { configureRingtone, startTone, stopTone, type RingtoneId } from '@/lib/tones'

// Pro Browser/Gerät gespeichert – wie beim Handy kann jedes Gerät anders klingeln
const PREF_KEY = 'kitmunicator:ringtone'
const DB_NAME = 'kitmunicator'
const STORE = 'files'
const CUSTOM_KEY = 'ringtone'
export const MAX_CUSTOM_BYTES = 5 * 1024 * 1024

interface Prefs {
  id: RingtoneId
  volume: number
  customName: string | null
}

const prefs = ref<Prefs>(readPrefs())
const previewing = ref(false)
let customUrl: string | null = null
let previewTimer: ReturnType<typeof setTimeout> | null = null
let initialized = false

function readPrefs(): Prefs {
  const fallback: Prefs = { id: 'classic', volume: 0.8, customName: null }
  try {
    return { ...fallback, ...JSON.parse(localStorage.getItem(PREF_KEY) ?? '{}') }
  } catch {
    return fallback
  }
}

function savePrefs() {
  try {
    localStorage.setItem(PREF_KEY, JSON.stringify(prefs.value))
  } catch {
    // Dann gilt die Auswahl nur für diese Sitzung
  }
}

// ── IndexedDB für die eigene Datei (localStorage ist dafür zu klein) ─────────

function openDb(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB_NAME, 1)
    req.onupgradeneeded = () => req.result.createObjectStore(STORE)
    req.onsuccess = () => resolve(req.result)
    req.onerror = () => reject(req.error)
  })
}

async function dbRequest<T>(mode: IDBTransactionMode, run: (store: IDBObjectStore) => IDBRequest<T>): Promise<T> {
  const db = await openDb()
  return new Promise((resolve, reject) => {
    const req = run(db.transaction(STORE, mode).objectStore(STORE))
    req.onsuccess = () => resolve(req.result)
    req.onerror = () => reject(req.error)
  })
}

function setCustomBlob(blob: Blob | null) {
  if (customUrl) URL.revokeObjectURL(customUrl)
  customUrl = blob ? URL.createObjectURL(blob) : null
  configureRingtone({ customUrl })
}

export function useRingtone() {
  async function init() {
    if (initialized) return
    initialized = true
    configureRingtone({ id: prefs.value.id, volume: prefs.value.volume })
    if (prefs.value.customName) {
      try {
        setCustomBlob((await dbRequest<Blob | undefined>('readonly', s => s.get(CUSTOM_KEY))) ?? null)
      } catch {
        setCustomBlob(null)
      }
    }
  }

  function select(id: RingtoneId) {
    prefs.value = { ...prefs.value, id }
  }

  function setVolume(volume: number) {
    prefs.value = { ...prefs.value, volume }
  }

  /** Gibt eine Fehlermeldung zurück oder null */
  async function uploadCustom(file: File): Promise<string | null> {
    if (!file.type.startsWith('audio/')) return 'Bitte eine Audiodatei wählen (MP3, WAV, OGG …).'
    if (file.size > MAX_CUSTOM_BYTES) return 'Die Datei ist zu groß (max. 5 MB).'
    try {
      await dbRequest('readwrite', s => s.put(file, CUSTOM_KEY))
    } catch {
      return 'Speichern im Browser fehlgeschlagen.'
    }
    setCustomBlob(file)
    prefs.value = { ...prefs.value, id: 'custom', customName: file.name }
    return null
  }

  async function removeCustom() {
    try {
      await dbRequest('readwrite', s => s.delete(CUSTOM_KEY))
    } catch {
      // Verwaiste Datei stört nicht, wird beim nächsten Upload überschrieben
    }
    setCustomBlob(null)
    prefs.value = { ...prefs.value, id: prefs.value.id === 'custom' ? 'classic' : prefs.value.id, customName: null }
  }

  function stopPreview() {
    if (previewTimer) { clearTimeout(previewTimer); previewTimer = null }
    if (previewing.value) stopTone()
    previewing.value = false
  }

  function togglePreview() {
    if (previewing.value) return stopPreview()
    startTone('ringtone')
    previewing.value = true
    previewTimer = setTimeout(stopPreview, 7000)
  }

  return { prefs, previewing, init, select, setVolume, uploadCustom, removeCustom, togglePreview, stopPreview }
}

watch(prefs, (p) => {
  configureRingtone({ id: p.id, volume: p.volume })
  savePrefs()
}, { deep: true })
