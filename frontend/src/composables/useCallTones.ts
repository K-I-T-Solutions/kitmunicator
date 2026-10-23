import { onBeforeUnmount, watch } from 'vue'
import { usePhone } from '@/composables/usePhone'
import { useRingtone } from '@/composables/useRingtone'
import { startTone, stopTone, unlockAudioOnInteraction } from '@/lib/tones'

/** Klingelton bei eingehenden Anrufen, Freizeichen beim Wählen. Einmal in der App-Shell. */
export function useCallTones(): void {
  const { callState } = usePhone()
  const { init, stopPreview } = useRingtone()

  init()
  unlockAudioOnInteraction()

  watch(callState, (state) => {
    // Eine laufende Vorschau aus den Einstellungen darf den echten Anruf nicht überdecken
    stopPreview()
    if (state === 'incoming') startTone('ringtone')
    else if (state === 'calling') startTone('ringback')
    else stopTone()
  })

  onBeforeUnmount(stopTone)
}
