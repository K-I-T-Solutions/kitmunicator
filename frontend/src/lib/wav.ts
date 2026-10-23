// Beliebiges Audio (Aufnahme oder Datei) → WAV 16 kHz / 16 bit / mono.
// Das ist das .wav16-Format, das Asterisk ohne Umrechnung abspielt.

export const GREETING_SAMPLE_RATE = 16_000

export async function toGreetingWav(input: Blob): Promise<{ wav: Blob; seconds: number }> {
  const decodeCtx = new AudioContext()
  let decoded: AudioBuffer
  try {
    decoded = await decodeCtx.decodeAudioData(await input.arrayBuffer())
  } finally {
    decodeCtx.close().catch(() => {})
  }

  // Resampling + Downmix auf Mono übernimmt der OfflineAudioContext
  const frames = Math.ceil(decoded.duration * GREETING_SAMPLE_RATE)
  const offline = new OfflineAudioContext(1, frames, GREETING_SAMPLE_RATE)
  const source = offline.createBufferSource()
  source.buffer = decoded
  source.connect(offline.destination)
  source.start()
  const rendered = await offline.startRendering()

  return { wav: encodeWav(normalize(rendered.getChannelData(0))), seconds: rendered.duration }
}

/** Auf -1 dBFS anheben, damit leise Laptop-Mikrofone am Telefon verständlich sind */
function normalize(samples: Float32Array): Float32Array {
  let peak = 0
  for (const s of samples) peak = Math.max(peak, Math.abs(s))
  if (peak < 0.01) return samples // praktisch Stille – nicht Rauschen aufblasen
  const gain = Math.min(0.89 / peak, 8)
  return samples.map(s => s * gain)
}

function encodeWav(samples: Float32Array): Blob {
  const buffer = new ArrayBuffer(44 + samples.length * 2)
  const view = new DataView(buffer)
  const ascii = (offset: number, text: string) => {
    for (let i = 0; i < text.length; i++) view.setUint8(offset + i, text.charCodeAt(i))
  }
  ascii(0, 'RIFF')
  view.setUint32(4, 36 + samples.length * 2, true)
  ascii(8, 'WAVE')
  ascii(12, 'fmt ')
  view.setUint32(16, 16, true)            // fmt-Chunk-Größe
  view.setUint16(20, 1, true)             // PCM
  view.setUint16(22, 1, true)             // mono
  view.setUint32(24, GREETING_SAMPLE_RATE, true)
  view.setUint32(28, GREETING_SAMPLE_RATE * 2, true)
  view.setUint16(32, 2, true)
  view.setUint16(34, 16, true)
  ascii(36, 'data')
  view.setUint32(40, samples.length * 2, true)
  samples.forEach((s, i) => {
    const clamped = Math.max(-1, Math.min(1, s))
    view.setInt16(44 + i * 2, clamped < 0 ? clamped * 0x8000 : clamped * 0x7fff, true)
  })
  return new Blob([buffer], { type: 'audio/wav' })
}
