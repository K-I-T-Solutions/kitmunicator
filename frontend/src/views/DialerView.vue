<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { usePhone } from '@/composables/usePhone'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const {
  callState, remoteNumber, isMuted, isOnHold,
  callDurationSeconds, formatDuration,
  call, hangup, mute, hold,
} = usePhone()

const dialInput = ref('')
const recentCalls = ref<Array<{ number: string; direction: string; status: string; started_at: string; duration_seconds: number }>>([])

const isActive = computed(() => ['calling', 'connected', 'incoming'].includes(callState.value))

function pressKey(key: string) {
  if (dialInput.value.length < 20) dialInput.value += key
}
function deleteLast() {
  dialInput.value = dialInput.value.slice(0, -1)
}

async function startCall() {
  if (!dialInput.value) return
  await call(dialInput.value)
}

async function loadRecentCalls() {
  const res = await fetch('/api/telephony/cdr?limit=20', { headers: auth.getAuthHeader() })
  if (res.ok) recentCalls.value = await res.json()
}

onMounted(loadRecentCalls)

const keys = [
  ['1', '2', '3'],
  ['4', '5', '6'],
  ['7', '8', '9'],
  ['*', '0', '#'],
]

function callStatusLabel(state: string): string {
  const labels: Record<string, string> = {
    idle:       'Bereit',
    registering:'Verbinde...',
    registered: 'Bereit',
    calling:    'Wähle...',
    incoming:   'Eingehend',
    connected:  'Verbunden',
    error:      'Fehler',
  }
  return labels[state] ?? state
}

function directionIcon(dir: string): string {
  if (dir === 'inbound') return '↙'
  if (dir === 'outbound') return '↗'
  return '↔'
}
</script>

<template>
  <div class="dialer-page">

    <!-- Linke Spalte: Wähler -->
    <div class="dialer-panel">

      <!-- Call-State-Display -->
      <div class="state-display" :class="callState">
        <template v-if="isActive">
          <div class="remote-number">{{ remoteNumber }}</div>
          <div class="call-status">{{ callStatusLabel(callState) }}</div>
          <div v-if="callState === 'connected'" class="call-duration">
            {{ formatDuration(callDurationSeconds) }}
          </div>
        </template>
        <template v-else>
          <div class="dial-input" :class="{ placeholder: !dialInput }">
            {{ dialInput || 'Nummer eingeben' }}
          </div>
          <div class="sip-state">{{ callStatusLabel(callState) }}</div>
        </template>
      </div>

      <!-- Keypad -->
      <div v-if="!isActive" class="keypad">
        <div v-for="row in keys" :key="row.join()" class="keypad-row">
          <button
            v-for="key in row"
            :key="key"
            class="key"
            @click="pressKey(key)"
          >
            {{ key }}
          </button>
        </div>
      </div>

      <!-- Aktions-Buttons -->
      <div class="actions">
        <template v-if="!isActive">
          <button class="btn-delete" @click="deleteLast" :disabled="!dialInput">⌫</button>
          <button class="btn-call" @click="startCall" :disabled="!dialInput">☎</button>
        </template>
        <template v-else>
          <button
            class="btn-action"
            :class="{ active: isMuted }"
            @click="mute()"
            title="Stummschalten"
          >
            {{ isMuted ? '🔇' : '🎙' }}
          </button>
          <button
            class="btn-action"
            :class="{ active: isOnHold }"
            @click="hold()"
            title="Halten"
          >
            {{ isOnHold ? '▶' : '⏸' }}
          </button>
          <button class="btn-hangup" @click="hangup()">✕</button>
        </template>
      </div>
    </div>

    <!-- Rechte Spalte: Letzte Anrufe -->
    <div class="recent-panel">
      <h2 class="recent-title">Letzte Anrufe</h2>

      <div v-if="recentCalls.length === 0" class="empty">
        Keine Anrufe vorhanden
      </div>

      <ul v-else class="call-list">
        <li
          v-for="cdr in recentCalls"
          :key="cdr.started_at"
          class="call-item"
          @click="dialInput = cdr.number"
        >
          <span class="dir-icon" :class="cdr.direction">
            {{ directionIcon(cdr.direction) }}
          </span>
          <div class="call-info">
            <span class="call-number">{{ cdr.number }}</span>
            <span class="call-meta">
              {{ new Date(cdr.started_at).toLocaleString('de-DE', { dateStyle: 'short', timeStyle: 'short' }) }}
              · {{ formatDuration(cdr.duration_seconds) }}
            </span>
          </div>
          <span class="call-status-badge" :class="cdr.status">{{ cdr.status }}</span>
        </li>
      </ul>
    </div>
  </div>
</template>

<style scoped>
.dialer-page {
  display: grid;
  grid-template-columns: 320px 1fr;
  gap: var(--space-6);
  max-width: 900px;
}

/* ── Dialer-Panel ── */
.dialer-panel {
  background: var(--kit-surface);
  border: 1px solid var(--kit-border);
  border-radius: var(--radius-lg);
  padding: var(--space-6);
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.state-display {
  background: var(--kit-surface-2);
  border-radius: var(--radius);
  padding: var(--space-4);
  text-align: center;
  min-height: 96px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--space-1);
  transition: background var(--transition);
}
.state-display.connected { background: rgba(34, 197, 94, 0.08); }
.state-display.calling   { background: rgba(245, 158, 11, 0.08); }
.state-display.incoming  { background: rgba(79, 110, 247, 0.08); }

.dial-input {
  font-size: var(--text-2xl);
  font-family: var(--font-mono);
  font-weight: 600;
  letter-spacing: 0.05em;
}
.dial-input.placeholder { color: var(--kit-text-muted); font-weight: 400; }

.remote-number { font-size: var(--text-2xl); font-weight: 600; }
.call-status   { font-size: var(--text-sm); color: var(--kit-text-muted); }
.call-duration { font-size: var(--text-lg); font-family: var(--font-mono); color: var(--kit-success); }
.sip-state     { font-size: var(--text-xs); color: var(--kit-text-muted); }

/* Keypad */
.keypad { display: flex; flex-direction: column; gap: var(--space-2); }
.keypad-row { display: grid; grid-template-columns: repeat(3, 1fr); gap: var(--space-2); }

.key {
  background: var(--kit-surface-2);
  border: 1px solid var(--kit-border);
  border-radius: var(--radius);
  padding: var(--space-3);
  font-size: var(--text-xl);
  font-weight: 500;
  transition: background var(--transition), transform var(--transition);
}
.key:hover { background: var(--kit-border); }
.key:active { transform: scale(0.95); }

/* Aktions-Buttons */
.actions {
  display: flex;
  gap: var(--space-3);
  justify-content: center;
  align-items: center;
}

.btn-call, .btn-hangup {
  width: 56px; height: 56px;
  border-radius: var(--radius-full);
  font-size: var(--text-xl);
  display: flex; align-items: center; justify-content: center;
  transition: transform var(--transition), background var(--transition);
}
.btn-call:hover, .btn-hangup:hover { transform: scale(1.08); }
.btn-call:disabled { opacity: 0.4; pointer-events: none; }

.btn-call   { background: var(--kit-success); color: white; }
.btn-hangup { background: var(--kit-danger);  color: white; }

.btn-delete {
  width: 44px; height: 44px;
  border-radius: var(--radius-full);
  font-size: var(--text-lg);
  background: var(--kit-surface-2);
  color: var(--kit-text-muted);
  transition: color var(--transition);
}
.btn-delete:hover { color: var(--kit-text); }
.btn-delete:disabled { opacity: 0.3; pointer-events: none; }

.btn-action {
  width: 44px; height: 44px;
  border-radius: var(--radius-full);
  font-size: var(--text-lg);
  background: var(--kit-surface-2);
  border: 1px solid var(--kit-border);
  transition: background var(--transition), border-color var(--transition);
}
.btn-action.active {
  background: var(--kit-accent-muted);
  border-color: var(--kit-accent);
}

/* ── Recent Calls ── */
.recent-panel {
  background: var(--kit-surface);
  border: 1px solid var(--kit-border);
  border-radius: var(--radius-lg);
  padding: var(--space-6);
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.recent-title {
  font-size: var(--text-base);
  font-weight: 600;
}

.empty {
  color: var(--kit-text-muted);
  font-size: var(--text-sm);
  text-align: center;
  padding: var(--space-8) 0;
}

.call-list {
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.call-item {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-3);
  border-radius: var(--radius);
  cursor: pointer;
  transition: background var(--transition);
}
.call-item:hover { background: var(--kit-surface-2); }

.dir-icon {
  font-size: var(--text-lg);
  width: 24px;
  text-align: center;
  flex-shrink: 0;
}
.dir-icon.inbound  { color: var(--kit-success); }
.dir-icon.outbound { color: var(--kit-accent); }
.dir-icon.internal { color: var(--kit-text-muted); }

.call-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.call-number { font-size: var(--text-sm); font-weight: 500; }
.call-meta   { font-size: var(--text-xs); color: var(--kit-text-muted); }

.call-status-badge {
  font-size: var(--text-xs);
  padding: 2px var(--space-2);
  border-radius: var(--radius-sm);
  background: var(--kit-surface-2);
  color: var(--kit-text-muted);
}
.call-status-badge.answered  { color: var(--kit-success); }
.call-status-badge.no_answer { color: var(--kit-warning); }
.call-status-badge.busy      { color: var(--kit-danger); }
</style>
