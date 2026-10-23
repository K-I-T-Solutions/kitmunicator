import { reactive, ref } from 'vue'
import { useAuthStore } from '@/stores/auth'

export type PresenceStatus = 'available' | 'busy' | 'away' | 'dnd'
export type PhoneStatus = 'idle' | 'ringing' | 'in_call' | 'offline'

/** Was ein Anrufer erwartet — passt zum Dialplan (_10XX). Leer = klingelt normal. */
export function reachabilityNotice(status: PresenceStatus, phone: PhoneStatus): string {
  if (phone === 'offline') return 'Nicht angemeldet – du landest auf der Mailbox'
  if (status === 'dnd') return 'Nicht stören – du landest auf der Mailbox'
  if (phone === 'in_call') return 'Gerade im Gespräch'
  if (status === 'away') return 'Abwesend – evtl. nicht am Platz'
  return ''
}

export const STATUS_LABELS: Record<PresenceStatus, string> = {
  available: 'Verfügbar',
  busy:      'Beschäftigt',
  away:      'Abwesend',
  dnd:       'Nicht stören',
}

export interface TeamMember {
  user_id: string
  username: string
  extension: string
  status: PresenceStatus
  phone_status: PhoneStatus
  updated_at: string | null
}

// ── Singleton-State (einmal für die gesamte App) ──────────────────────────────

const statuses = reactive<Record<string, PresenceStatus>>({})
const phoneStatuses = reactive<Record<string, PhoneStatus>>({})
// Alle aktiven SIP-User inkl. des eigenen Accounts – gefüllt von loadTeam()
const team = ref<TeamMember[]>([])
const subscribedIds = new Set<string>()
let ws: WebSocket | null = null

export interface MissedCallEvent {
  caller_number: string
  caller_name: string | null
  voicemail_id: number | null
  at: string
}
const missedCallListeners = new Set<(e: MissedCallEvent) => void>()

/** Verpasste Anrufe (Server-Event über den Presence-Socket). Gibt die Abmeldung zurück. */
export function onMissedCall(listener: (e: MissedCallEvent) => void): () => void {
  missedCallListeners.add(listener)
  return () => missedCallListeners.delete(listener)
}
let reconnectTimer: ReturnType<typeof setTimeout> | null = null

function _send(data: unknown) {
  if (ws?.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify(data))
  }
}

function _connect(token: string) {
  if (reconnectTimer) { clearTimeout(reconnectTimer); reconnectTimer = null }
  const url = import.meta.env.VITE_API_WS_URL + '/presence/ws/presence'
  ws = new WebSocket(url)

  ws.onopen = () => {
    _send({ type: 'auth', token })
    if (subscribedIds.size > 0) {
      _send({ type: 'subscribe', user_ids: [...subscribedIds] })
    }
  }

  ws.onmessage = (e: MessageEvent) => {
    const msg = JSON.parse(e.data as string) as {
      type: string
      user_id: string
      status: PresenceStatus
      phone_status: PhoneStatus
    }
    if (msg.type === 'presence') {
      statuses[msg.user_id] = msg.status
      if (msg.phone_status) phoneStatuses[msg.user_id] = msg.phone_status
    } else if (msg.type === 'missed_call') {
      const event = msg as unknown as MissedCallEvent
      missedCallListeners.forEach(listener => listener(event))
    }
  }

  ws.onclose = () => {
    reconnectTimer = setTimeout(() => {
      const auth = useAuthStore()
      if (auth.token) _connect(auth.token)
    }, 3000)
  }
}

// ── Composable ────────────────────────────────────────────────────────────────

export function usePresence() {
  const auth = useAuthStore()

  function init() {
    if (!ws && auth.token) _connect(auth.token)
  }

  function subscribe(userIds: string[]) {
    const fresh = userIds.filter(id => !subscribedIds.has(id))
    fresh.forEach(id => subscribedIds.add(id))
    if (fresh.length > 0) _send({ type: 'subscribe', user_ids: fresh })
  }

  async function setMyStatus(status: PresenceStatus) {
    if (auth.userId) statuses[auth.userId] = status
    await fetch('/api/presence/me', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json', ...auth.getAuthHeader() },
      body: JSON.stringify({ status }),
    })
  }

  async function loadTeam(): Promise<TeamMember[]> {
    const res = await fetch('/api/presence/team', { headers: auth.getAuthHeader() })
    if (!res.ok) return []
    const members: TeamMember[] = await res.json()
    for (const m of members) {
      statuses[m.user_id] = m.status
      phoneStatuses[m.user_id] = m.phone_status
    }
    team.value = members
    return members
  }

  /** Durchwahl → Team-Mitglied (für Anrufer-Namen) */
  function memberByExtension(extension: string | null | undefined): TeamMember | undefined {
    if (!extension) return undefined
    return team.value.find(m => m.extension === extension)
  }

  return { statuses, phoneStatuses, team, init, subscribe, setMyStatus, loadTeam, memberByExtension }
}
