import { computed } from 'vue'
import { usePhone } from '@/composables/usePhone'
import { reachabilityNotice, usePresence } from '@/composables/usePresence'

export type SipState = 'offline' | 'connecting' | 'registered' | 'error'

/** Abgeleitete Anzeige-Werte für SIP-Status und laufenden Anruf */
export function useActiveCall() {
  const { callState, remoteNumber, remoteName, isOnHold } = usePhone()
  const { memberByExtension, statuses, phoneStatuses } = usePresence()

  const sipState = computed<SipState>(() => {
    switch (callState.value) {
      case 'idle': return 'offline'
      case 'registering': return 'connecting'
      case 'error': return 'error'
      default: return 'registered'
    }
  })

  /** Ausgehender oder angenommener Anruf (nicht: klingelnd eingehend) */
  const hasActiveCall = computed(() => callState.value === 'calling' || callState.value === 'connected')

  const remoteDisplayName = computed(() =>
    remoteName.value
    || memberByExtension(remoteNumber.value)?.username
    || remoteNumber.value
    || 'Unbekannt',
  )

  const callStatusLabel = computed(() => {
    if (callState.value === 'calling') return 'Wähle…'
    if (callState.value === 'connected') return isOnHold.value ? 'Gehalten' : 'Verbunden'
    return ''
  })

  /** Beim Wählen: Hinweis, wenn der Kollege nicht normal erreichbar ist */
  const calleeNotice = computed(() => {
    if (callState.value !== 'calling') return ''
    const member = memberByExtension(remoteNumber.value)
    if (!member) return ''
    return reachabilityNotice(
      statuses[member.user_id] ?? member.status,
      phoneStatuses[member.user_id] ?? member.phone_status,
    )
  })

  return { sipState, hasActiveCall, remoteDisplayName, callStatusLabel, calleeNotice }
}
