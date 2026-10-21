import { ref } from 'vue'
import { useAuthStore } from '@/stores/auth'

export interface SipInfo {
  id: number
  username: string
  extension: string
  display_name: string | null
  email: string | null
  is_active: boolean
  online: boolean | null
}

export interface AdminUser {
  user_id: string
  username: string
  display_name: string
  email: string | null
  enabled: boolean
  in_keycloak: boolean
  sip: SipInfo | null
}

export interface RingGroup {
  id: number
  name: string
  extension: string
  ring_timeout: number
  fallback_extension: string | null
  inbound_number: string | null
  inbound_catch_all: boolean
  members: { id: number; username: string; extension: string; display_name: string | null; is_active: boolean }[]
}

export interface RingGroupInput {
  name: string
  extension: string
  ring_timeout: number
  fallback_extension: string | null
  inbound_number: string | null
  inbound_catch_all: boolean
  member_ids: number[]
}

export interface PbxStatus {
  endpoints: { username: string; extension: string | null; display_name: string | null; state: string }[]
  calls: { channel: string; caller: string; caller_name: string | null; connected: string | null; state: string; since: string | null }[]
  trunk_state: string | null
  asterisk_error: string | null
}

/** Verwaltung (Rolle telephony_admin) – dünne Hülle um /api/admin */
export function useAdmin() {
  const auth = useAuthStore()

  const users = ref<AdminUser[]>([])
  const keycloakError = ref<string | null>(null)
  const nextExtension = ref<string | null>(null)
  const loadState = ref<'loading' | 'ready' | 'error'>('loading')

  async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
    const res = await fetch(`/api/admin${path}`, {
      ...init,
      headers: { ...auth.getAuthHeader(), 'Content-Type': 'application/json', ...init.headers },
    })
    if (!res.ok) {
      const body = await res.json().catch(() => null)
      const detail = body?.detail
      throw new Error(typeof detail === 'string' ? detail : Array.isArray(detail) ? detail[0]?.msg : `Fehler ${res.status}`)
    }
    return (res.status === 204 ? undefined : await res.json()) as T
  }

  async function loadUsers() {
    try {
      const data = await api<{ users: AdminUser[]; keycloak_error: string | null; next_extension: string | null }>('/users')
      users.value = data.users
      keycloakError.value = data.keycloak_error
      nextExtension.value = data.next_extension
      loadState.value = 'ready'
    } catch {
      loadState.value = 'error'
    }
  }

  const assignSip = (userId: string, extension: string, displayName: string) =>
    api<SipInfo>(`/users/${userId}/sip`, { method: 'POST', body: JSON.stringify({ extension, display_name: displayName }) })

  const updateSip = (id: number, patch: Partial<Pick<SipInfo, 'extension' | 'display_name' | 'email' | 'is_active'>>) =>
    api<SipInfo>(`/sip/${id}`, { method: 'PATCH', body: JSON.stringify(patch) })

  const resetPassword = (id: number) => api<void>(`/sip/${id}/password`, { method: 'POST' })
  const deleteSip = (id: number) => api<void>(`/sip/${id}`, { method: 'DELETE' })
  const loadStatus = () => api<PbxStatus>('/status')

  const loadGroups = () => api<RingGroup[]>('/groups')
  const nextGroupExtension = async () => (await api<{ extension: string | null }>('/groups/next-extension')).extension
  const saveGroup = (input: RingGroupInput, id?: number) =>
    api<RingGroup>(id ? `/groups/${id}` : '/groups', { method: id ? 'PUT' : 'POST', body: JSON.stringify(input) })
  const deleteGroup = (id: number) => api<void>(`/groups/${id}`, { method: 'DELETE' })

  return {
    users, keycloakError, nextExtension, loadState,
    loadUsers, assignSip, updateSip, resetPassword, deleteSip, loadStatus,
    loadGroups, nextGroupExtension, saveGroup, deleteGroup,
  }
}
