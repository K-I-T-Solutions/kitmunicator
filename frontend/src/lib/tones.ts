// Klingelton und Freizeichen per Web Audio – Asterisk schickt beim Klingeln
// kein Early Media, der Client muss beides selbst erzeugen.

export type ToneKind = 'ringtone' | 'ringback'
export type RingtoneId = 'classic' | 'digital' | 'soft' | 'landline' | 'custom'

interface Note {
  freqs: number[]
  start: number // Sekunden ab Periodenbeginn
  length: number
}

interface Pattern {
  notes: Note[]
  period: number
  volume: number
  wave: OscillatorType
  /** Ausklingen statt gleichmäßigem Ton (glockenartig) */
  decay?: boolean
}

const twoTone = (offset: number): Note[] => [
  { freqs: [880], start: offset, length: 0.14 },
  { freqs: [1175], start: offset + 0.16, length: 0.14 },
  { freqs: [880], start: offset + 0.32, length: 0.14 },
  { freqs: [1175], start: offset + 0.48, length: 0.14 },
]
const tripleBeep = (offset: number): Note[] =>
  [0, 0.14, 0.28].map(t => ({ freqs: [1400], start: offset + t, length: 0.08 }))

export const RINGTONES: Record<Exclude<RingtoneId, 'custom'>, Pattern & { label: string }> = {
  classic: { label: 'Klassisch', notes: [...twoTone(0), ...twoTone(1)], period: 3.5, volume: 0.18, wave: 'sine' },
  digital: { label: 'Digital', notes: [...tripleBeep(0), ...tripleBeep(0.6)], period: 2.5, volume: 0.07, wave: 'square' },
  soft: {
    label: 'Sanft',
    notes: [1047, 1319, 1568, 2093].map((f, i) => ({ freqs: [f], start: i * 0.18, length: 0.7 })),
    period: 3,
    volume: 0.2,
    wave: 'sine',
    decay: true,
  },
  // Amerikanisches Festnetz-Klingeln: 440 + 480 Hz, 2 s an, 4 s aus
  landline: { label: 'Festnetz', notes: [{ freqs: [440, 480], start: 0, length: 2 }], period: 6, volume: 0.1, wave: 'sine' },
}

// Deutsches Freizeichen: 425 Hz, 1 s Ton, 4 s Pause
const RINGBACK: Pattern = { notes: [{ freqs: [425], start: 0, length: 1 }], period: 5, volume: 0.12, wave: 'sine' }

interface RingtoneConfig {
  id: RingtoneId
  /** 0–1 */
  volume: number
  customUrl: string | null
}

let config: RingtoneConfig = { id: 'classic', volume: 0.8, customUrl: null }
let ctx: AudioContext | null = null
let timer: ReturnType<typeof setInterval> | null = null
let output: GainNode | null = null
const customAudio = new Audio()
customAudio.loop = true

export function configureRingtone(next: Partial<RingtoneConfig>): void {
  config = { ...config, ...next }
  customAudio.volume = config.volume
}

function context(): AudioContext {
  ctx ??= new AudioContext()
  return ctx
}

/**
 * Browser lassen Audio erst nach einer Nutzeraktion zu. Nach dem Keycloak-Redirect
 * gab es noch keine – daher beim ersten Klick/Tastendruck entsperren, damit ein
 * eingehender Anruf später klingeln kann.
 */
export function unlockAudioOnInteraction(): void {
  const unlock = () => {
    const c = context()
    if (c.state === 'suspended') c.resume().catch(() => {})
    if (c.state === 'running') {
      window.removeEventListener('pointerdown', unlock)
      window.removeEventListener('keydown', unlock)
    }
  }
  window.addEventListener('pointerdown', unlock)
  window.addEventListener('keydown', unlock)
}

function playPeriod(c: AudioContext, pattern: Pattern, out: GainNode): void {
  const t0 = c.currentTime + 0.02
  for (const note of pattern.notes) {
    const begin = t0 + note.start
    const end = begin + note.length
    const env = c.createGain()
    env.gain.setValueAtTime(0, begin)
    env.gain.linearRampToValueAtTime(pattern.volume, begin + 0.01)
    if (pattern.decay) {
      env.gain.exponentialRampToValueAtTime(0.0001, end)
    } else {
      // Kurze Rampen gegen Knacken
      env.gain.setValueAtTime(pattern.volume, end - 0.02)
      env.gain.linearRampToValueAtTime(0, end)
    }
    env.connect(out)
    for (const freq of note.freqs) {
      const osc = c.createOscillator()
      osc.type = pattern.wave
      osc.frequency.value = freq
      osc.connect(env)
      osc.start(begin)
      osc.stop(end)
    }
  }
}

function startPattern(pattern: Pattern, volume: number): void {
  const c = context()
  if (c.state === 'suspended') c.resume().catch(() => {})
  output = c.createGain()
  output.gain.value = volume
  output.connect(c.destination)
  const out = output
  playPeriod(c, pattern, out)
  timer = setInterval(() => playPeriod(c, pattern, out), pattern.period * 1000)
}

export function startTone(kind: ToneKind): void {
  stopTone()
  if (kind === 'ringback') {
    startPattern(RINGBACK, 1)
    return
  }
  if (config.id === 'custom' && config.customUrl) {
    customAudio.src = config.customUrl
    customAudio.currentTime = 0
    // Datei nicht abspielbar → auf den Standardton ausweichen, damit es trotzdem klingelt
    customAudio.play().catch(() => startPattern(RINGTONES.classic, config.volume))
    return
  }
  const id = config.id === 'custom' ? 'classic' : config.id
  startPattern(RINGTONES[id], config.volume)
}

export function stopTone(): void {
  if (timer) { clearInterval(timer); timer = null }
  // Bereits geplante Noten sofort verstummen lassen
  output?.disconnect()
  output = null
  customAudio.pause()
}
