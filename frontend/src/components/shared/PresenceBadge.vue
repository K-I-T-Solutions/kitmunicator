<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from 'vue'
import { useAuthStore } from '@/stores/auth'

type Status = 'available' | 'busy' | 'away' | 'dnd'
type PhoneStatus = 'idle' | 'ringing' | 'in_call' | 'offline'

const props = defineProps<{
  userId: string
  editable?: boolean
}>()

const auth = useAuthStore()
const status = ref<Status>('available')
const phoneStatus = ref<PhoneStatus>('offline')
let ws: WebSocket | null = null

const statusLabels: Record<Status, string> = {
  available: 'Verfügbar',
  busy:      'Beschäftigt',
  away:      'Abwesend',
  dnd:       'Nicht stören',
}

function connect() {
  const wsUrl = import.meta.env.VITE_API_WS_URL + '/presence/ws/presence'
  ws = new WebSocket(wsUrl)

  ws.onopen = () => {
    ws?.send(JSON.stringify({ type: 'auth', token: auth.token }))
    ws?.send(JSON.stringify({ type: 'subscribe', user_ids: [props.userId] }))
  }

  ws.onmessage = (event: MessageEvent) => {
    const msg = JSON.parse(event.data as string) as {
      type: string; user_id: string; status: Status; phone_status: PhoneStatus
    }
    if (msg.type === 'presence' && msg.user_id === props.userId) {
      status.value = msg.status
      if (msg.phone_status) phoneStatus.value = msg.phone_status
    }
  }

  ws.onclose = () => {
    setTimeout(connect, 3000)
  }
}

async function setStatus(newStatus: Status) {
  status.value = newStatus
  await fetch('/api/presence/me', {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json', ...auth.getAuthHeader() },
    body: JSON.stringify({ status: newStatus }),
  })
}

onMounted(connect)
onUnmounted(() => ws?.close())
watch(() => props.userId, () => {
  ws?.close()
  connect()
})
</script>

<template>
  <div class="presence-badge" :class="{ editable }">
    <span class="dot-wrap">
      <span class="dot" :class="status" :title="statusLabels[status]" />
      <span
        v-if="phoneStatus === 'ringing' || phoneStatus === 'in_call'"
        class="phone-indicator"
        :class="phoneStatus"
        :title="phoneStatus === 'ringing' ? 'Klingelt' : 'Im Gespräch'"
      >📞</span>
    </span>

    <div v-if="editable" class="status-menu">
      <button
        v-for="(label, key) in statusLabels"
        :key="key"
        class="status-option"
        :class="{ active: status === key }"
        @click="setStatus(key as Status)"
      >
        <span class="dot" :class="key" />
        {{ label }}
      </button>
    </div>
  </div>
</template>

<style scoped>
.presence-badge {
  position: relative;
  display: inline-flex;
  align-items: center;
}

.dot-wrap {
  position: relative;
  display: inline-flex;
  align-items: center;
}

.dot {
  width: 10px;
  height: 10px;
  border-radius: var(--radius-full);
  flex-shrink: 0;
  transition: background var(--transition);
}
.dot.available { background: var(--presence-available); }
.dot.busy      { background: var(--presence-busy); }
.dot.away      { background: var(--presence-away); }
.dot.dnd       { background: var(--presence-dnd); }

.editable .dot { cursor: pointer; }

/* Telefon-Substatus */
.phone-indicator {
  position: absolute;
  bottom: -6px;
  right: -8px;
  font-size: 8px;
  line-height: 1;
  pointer-events: none;
}
.phone-indicator.ringing {
  animation: ring-pulse 0.8s ease-in-out infinite alternate;
}
@keyframes ring-pulse {
  from { opacity: 0.5; transform: scale(0.9); }
  to   { opacity: 1;   transform: scale(1.1); }
}

.status-menu {
  display: none;
  position: absolute;
  bottom: calc(100% + 8px);
  left: 0;
  background: var(--kit-surface-2);
  border: 1px solid var(--kit-border);
  border-radius: var(--radius);
  box-shadow: var(--shadow);
  padding: var(--space-1);
  min-width: 160px;
  z-index: 100;
}

.editable:hover .status-menu,
.editable:focus-within .status-menu {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.status-option {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-3);
  border-radius: var(--radius-sm);
  font-size: var(--text-sm);
  color: var(--kit-text-muted);
  transition: background var(--transition), color var(--transition);
  text-align: left;
  width: 100%;
}
.status-option:hover { background: var(--kit-surface); color: var(--kit-text); }
.status-option.active { color: var(--kit-text); }
</style>
