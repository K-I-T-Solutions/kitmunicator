import { reactive } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { usePhone } from '@/composables/usePhone'

export type PresenceStatus = 'available' | 'busy' | 'away' | 'dnd'

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
  updated_at: string | null
}

// ── Singleton-State (einmal für die gesamte App) ──────────────────────────────

const statuses = reactive<Record<string, PresenceStatus>>({})
const subscribedIds = new Set<string>()
let ws: WebSocket | null = null
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
    const msg = JSON.parse(e.data as string) as { type: string; user_id: string; status: PresenceStatus }
    if (msg.type === 'presence') {
      statuses[msg.user_id] = msg.status
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
    // Initialen Status in reactive Map übernehmen
    for (const m of members) statuses[m.user_id] = m.status
    return members
  }

  return { statuses, init, subscribe, setMyStatus, loadTeam }
}
