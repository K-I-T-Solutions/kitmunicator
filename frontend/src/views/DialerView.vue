<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import {
  ArrowDownLeft, ArrowLeftRight, ArrowUpRight, CircleAlert, Clock,
  Delete, Mic, MicOff, Pause, Phone, PhoneOff, Play,
} from 'lucide-vue-next'
import { useAuthStore } from '@/stores/auth'
import { usePhone } from '@/composables/usePhone'
import { usePresence } from '@/composables/usePresence'
import { useActiveCall } from '@/composables/useActiveCall'
import { formatCallTime, formatDuration } from '@/lib/format'

const auth = useAuthStore()
const {
  callState, remoteNumber, isMuted, isOnHold, isBusy,
  callDurationSeconds, call, hangup, mute, hold,
} = usePhone()
const { team } = usePresence()
const { hasActiveCall, remoteDisplayName, callStatusLabel } = useActiveCall()

// ── Wählfeld ────────────────────────────────────────────────────────────────

const dialInput = ref('')
const inputEl = ref<HTMLInputElement | null>(null)

const KEYS = [
  { d: '1', l: '' }, { d: '2', l: 'ABC' }, { d: '3', l: 'DEF' },
  { d: '4', l: 'GHI' }, { d: '5', l: 'JKL' }, { d: '6', l: 'MNO' },
  { d: '7', l: 'PQRS' }, { d: '8', l: 'TUV' }, { d: '9', l: 'WXYZ' },
  { d: '*', l: '' }, { d: '0', l: '+' }, { d: '#', l: '' },
]

function pressKey(key: string) {
  if (dialInput.value.length < 20) dialInput.value += key
}
function deleteLast() {
  dialInput.value = dialInput.value.slice(0, -1)
}
// Nur wählbare Zeichen zulassen (auch beim Einfügen)
function sanitize() {
  dialInput.value = dialInput.value.replace(/[^\d+*#]/g, '').slice(0, 20)
}

async function startCall() {
  if (!dialInput.value || isBusy.value) return
  await call(dialInput.value)
}

// ── Letzte Anrufe ───────────────────────────────────────────────────────────

interface CallRecord {
  id: number
  caller_number: string
  caller_name: string | null
  callee_number: string
  callee_name: string | null
  direction: 'inbound' | 'outbound' | 'internal'
  status: 'answered' | 'no_answer' | 'busy' | 'failed'
  started_at: string
  duration_seconds: number
}

const recentCalls = ref<CallRecord[]>([])
const cdrState = ref<'loading' | 'ready' | 'error'>('loading')
const tab = ref<'all' | 'missed'>('all')

const myExtension = computed(() => team.value.find(m => m.user_id === auth.userId)?.extension)

/** Interne Anrufe zählen als eingehend, wenn ich angerufen wurde */
function isIncoming(cdr: CallRecord): boolean {
  if (cdr.direction === 'internal') return cdr.callee_number === myExtension.value
  return cdr.direction === 'inbound'
}
function isMissed(cdr: CallRecord): boolean {
  return isIncoming(cdr) && cdr.status === 'no_answer'
}
function counterpartNumber(cdr: CallRecord): string {
  return isIncoming(cdr) ? cdr.caller_number : cdr.callee_number
}
function counterpartName(cdr: CallRecord): string | null {
  return isIncoming(cdr) ? cdr.caller_name : cdr.callee_name
}
function statusLabel(cdr: CallRecord): string {
  switch (cdr.status) {
    case 'answered': return 'Angenommen'
    case 'no_answer': return isIncoming(cdr) ? 'Verpasst' : 'Nicht erreicht'
    case 'busy': return 'Besetzt'
    default: return 'Fehlgeschlagen'
  }
}

const filteredCalls = computed(() =>
  tab.value === 'missed' ? recentCalls.value.filter(isMissed) : recentCalls.value,
)

function pickNumber(cdr: CallRecord) {
  dialInput.value = counterpartNumber(cdr)
  inputEl.value?.focus()
}

async function loadRecentCalls() {
  try {
    const res = await fetch('/api/telephony/cdr?limit=30', { headers: auth.getAuthHeader() })
    if (!res.ok) throw new Error(String(res.status))
    recentCalls.value = await res.json()
    cdrState.value = 'ready'
  } catch {
    cdrState.value = 'error'
  }
}

onMounted(loadRecentCalls)

// Nach Gesprächsende neu laden – das Backend schreibt den CDR kurz nach dem Auflegen
watch(callState, (state, prev) => {
  if (state === 'registered' && (prev === 'connected' || prev === 'calling' || prev === 'incoming')) {
    setTimeout(loadRecentCalls, 1500)
  }
})
</script>

<template>
  <div class="mx-auto grid max-w-6xl gap-6 px-4 py-6 md:px-6 lg:grid-cols-2">
    <!-- Wählfeld / laufender Anruf -->
    <section class="flex flex-col rounded-2xl border border-line/60 bg-surface p-5 md:p-6" aria-label="Wählfeld">
      <div v-if="hasActiveCall" class="flex animate-fade-in flex-col items-center py-6">
        <span class="mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-cyan-500/15 ring-1 ring-cyan-500/30">
          <Phone class="h-7 w-7 text-brand" />
        </span>
        <p class="text-lg font-semibold text-fg">{{ remoteDisplayName }}</p>
        <p v-if="remoteNumber && remoteNumber !== remoteDisplayName" class="mt-0.5 font-mono text-sm text-muted">{{ remoteNumber }}</p>
        <p class="mt-2 text-xs font-medium uppercase tracking-widest text-brand">{{ callStatusLabel }}</p>
        <p class="tabular mt-1 h-8 font-mono text-2xl text-fg">
          <template v-if="callState === 'connected'">{{ formatDuration(callDurationSeconds) }}</template>
        </p>

        <div class="mt-8 flex items-center gap-5">
          <button
            class="flex flex-col items-center gap-1.5 disabled:opacity-40"
            :class="isMuted ? 'text-accent-500' : 'text-muted'"
            :disabled="callState !== 'connected'"
            :aria-pressed="isMuted"
            @click="mute()"
          >
            <span
              class="flex h-14 w-14 items-center justify-center rounded-full transition-colors"
              :class="isMuted ? 'bg-accent-500/15 ring-1 ring-accent-500/30' : 'bg-raised hover:text-fg'"
            >
              <MicOff v-if="isMuted" class="h-5 w-5" />
              <Mic v-else class="h-5 w-5" />
            </span>
            <span class="text-[11px]">{{ isMuted ? 'Stumm an' : 'Stumm' }}</span>
          </button>
          <button
            class="flex flex-col items-center gap-1.5 disabled:opacity-40"
            :class="isOnHold ? 'text-amber-500' : 'text-muted'"
            :disabled="callState !== 'connected'"
            :aria-pressed="isOnHold"
            @click="hold()"
          >
            <span
              class="flex h-14 w-14 items-center justify-center rounded-full transition-colors"
              :class="isOnHold ? 'bg-amber-500/15 ring-1 ring-amber-500/30' : 'bg-raised hover:text-fg'"
            >
              <Play v-if="isOnHold" class="h-5 w-5" />
              <Pause v-else class="h-5 w-5" />
            </span>
            <span class="text-[11px]">{{ isOnHold ? 'Fortsetzen' : 'Halten' }}</span>
          </button>
          <button class="flex flex-col items-center gap-1.5 text-red-500" @click="hangup()">
            <span class="flex h-14 w-14 items-center justify-center rounded-full bg-red-500 text-white shadow-lg shadow-red-500/20 transition-colors hover:bg-red-600">
              <PhoneOff class="h-6 w-6" />
            </span>
            <span class="text-[11px]">Auflegen</span>
          </button>
        </div>
      </div>

      <form v-else class="mx-auto flex w-full max-w-sm flex-col" @submit.prevent="startCall">
        <div class="mb-4 flex items-center">
          <label for="dial-input" class="sr-only">Rufnummer</label>
          <input
            id="dial-input"
            ref="inputEl"
            v-model="dialInput"
            type="tel"
            inputmode="tel"
            autocomplete="off"
            placeholder="Nummer eingeben…"
            class="min-w-0 flex-1 bg-transparent font-mono text-3xl tracking-wider text-fg placeholder:text-subtle/70 focus:outline-none"
            @input="sanitize"
          />
          <button
            v-if="dialInput"
            type="button"
            class="ml-2 rounded-lg p-2 text-muted transition-colors hover:bg-raised hover:text-fg"
            aria-label="Letzte Ziffer löschen"
            @click="deleteLast"
          >
            <Delete class="h-5 w-5" />
          </button>
        </div>

        <div class="mb-5 grid grid-cols-3 gap-2.5">
          <button
            v-for="k in KEYS"
            :key="k.d"
            type="button"
            class="flex h-14 flex-col items-center justify-center rounded-xl border border-line/60 bg-raised/60 transition-all hover:border-line hover:bg-raised active:scale-95 md:h-16"
            @click="pressKey(k.d)"
          >
            <span class="font-mono text-xl font-medium text-fg">{{ k.d }}</span>
            <span v-if="k.l" class="text-[10px] tracking-widest text-subtle">{{ k.l }}</span>
          </button>
        </div>

        <button
          type="submit"
          class="flex items-center justify-center gap-2.5 rounded-xl bg-cyan-500 py-3.5 font-semibold text-navy-800 transition-colors hover:bg-cyan-400 disabled:cursor-not-allowed disabled:bg-raised disabled:text-subtle"
          :disabled="!dialInput || isBusy"
        >
          <Phone class="h-5 w-5" />
          Anrufen
        </button>
        <p class="mt-3 text-center text-xs text-subtle">Intern: 10xx · Extern: 0 oder +49</p>
      </form>
    </section>

    <!-- Letzte Anrufe -->
    <section class="flex min-h-[20rem] flex-col overflow-hidden rounded-2xl border border-line/60 bg-surface" aria-labelledby="recent-title">
      <div class="flex items-center justify-between px-5 pb-3 pt-5">
        <h2 id="recent-title" class="text-sm font-semibold text-fg">Letzte Anrufe</h2>
        <div class="flex gap-1 rounded-lg bg-raised p-0.5" role="tablist" aria-label="Filter">
          <button
            v-for="t in (['all', 'missed'] as const)"
            :key="t"
            role="tab"
            :aria-selected="tab === t"
            class="rounded-md px-3 py-1 text-xs font-medium transition-colors"
            :class="tab === t ? 'bg-surface text-fg shadow-sm' : 'text-muted hover:text-fg'"
            @click="tab = t"
          >
            {{ t === 'all' ? 'Alle' : 'Verpasst' }}
          </button>
        </div>
      </div>

      <div v-if="cdrState === 'loading'" class="space-y-1 px-5 pb-4" aria-busy="true">
        <div v-for="i in 5" :key="i" class="flex animate-pulse items-center gap-3 py-2.5">
          <span class="h-9 w-9 rounded-full bg-raised" />
          <span class="h-3 flex-1 rounded bg-raised" />
        </div>
      </div>

      <div v-else-if="cdrState === 'error'" class="flex flex-1 flex-col items-center justify-center px-4 py-12 text-center">
        <CircleAlert class="mb-2 h-6 w-6 text-subtle" />
        <p class="text-sm text-muted">Anrufliste konnte nicht geladen werden.</p>
        <button class="mt-2 text-sm text-brand hover:underline" @click="cdrState = 'loading'; loadRecentCalls()">Erneut versuchen</button>
      </div>

      <div v-else-if="filteredCalls.length === 0" class="flex flex-1 flex-col items-center justify-center px-4 py-12 text-center">
        <Clock class="mb-2 h-6 w-6 text-subtle" />
        <p class="text-sm text-muted">{{ tab === 'missed' ? 'Keine verpassten Anrufe.' : 'Noch keine Anrufe.' }}</p>
      </div>

      <ul v-else class="scrollbar-thin flex-1 overflow-y-auto pb-2">
        <li v-for="cdr in filteredCalls" :key="cdr.id" class="group flex items-center gap-1 pr-3 transition-colors hover:bg-raised/60">
          <button
            class="flex min-w-0 flex-1 items-center gap-3 py-3 pl-5 text-left"
            :title="`${counterpartNumber(cdr)} ins Wählfeld übernehmen`"
            @click="pickNumber(cdr)"
          >
            <span
              class="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-raised"
              :class="cdr.direction === 'internal' ? 'text-blue-500' : isIncoming(cdr) ? 'text-emerald-500' : 'text-brand'"
              :title="cdr.direction === 'internal' ? 'Intern' : isIncoming(cdr) ? 'Eingehend' : 'Ausgehend'"
            >
              <ArrowLeftRight v-if="cdr.direction === 'internal'" class="h-4 w-4" />
              <ArrowDownLeft v-else-if="isIncoming(cdr)" class="h-4 w-4" />
              <ArrowUpRight v-else class="h-4 w-4" />
            </span>
            <span class="min-w-0 flex-1">
              <span class="flex items-center gap-1.5">
                <span class="truncate text-sm font-medium" :class="isMissed(cdr) ? 'text-red-600 dark:text-red-400' : 'text-fg'">
                  {{ counterpartName(cdr) || counterpartNumber(cdr) }}
                </span>
                <CircleAlert v-if="isMissed(cdr)" class="h-3.5 w-3.5 shrink-0 text-red-500" />
              </span>
              <span v-if="counterpartName(cdr)" class="block truncate font-mono text-xs text-subtle">{{ counterpartNumber(cdr) }}</span>
            </span>
            <span class="shrink-0 text-right">
              <span
                class="block text-xs"
                :class="isMissed(cdr) ? 'font-medium text-red-600 dark:text-red-400' : cdr.status === 'busy' ? 'text-amber-600 dark:text-amber-400' : 'text-muted'"
              >{{ statusLabel(cdr) }}</span>
              <span class="tabular mt-0.5 block text-[11px] text-subtle">
                {{ formatCallTime(cdr.started_at) }}<template v-if="cdr.status === 'answered'"> · {{ formatDuration(cdr.duration_seconds) }}</template>
              </span>
            </span>
          </button>
          <button
            class="shrink-0 rounded-lg p-2 text-brand opacity-60 transition-opacity hover:bg-cyan-500/10 group-hover:opacity-100 disabled:opacity-20"
            :disabled="isBusy"
            :aria-label="`${counterpartName(cdr) || counterpartNumber(cdr)} anrufen`"
            @click="call(counterpartNumber(cdr), counterpartName(cdr) ?? undefined)"
          >
            <Phone class="h-4 w-4" />
          </button>
        </li>
      </ul>
    </section>
  </div>
</template>
