<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { CircleAlert, PhoneCall, Radio, Server } from 'lucide-vue-next'
import { useAdmin, type PbxStatus } from '@/composables/useAdmin'
import { formatDuration } from '@/lib/format'

const { loadStatus } = useAdmin()

const status = ref<PbxStatus | null>(null)
const failed = ref(false)
const now = ref(Date.now())

const REFRESH_MS = 5000
let refreshTimer: ReturnType<typeof setInterval> | null = null
let clockTimer: ReturnType<typeof setInterval> | null = null

async function refresh() {
  try {
    status.value = await loadStatus()
    failed.value = false
  } catch {
    failed.value = true
  }
}

const online = computed(() => status.value?.endpoints.filter(e => e.state === 'online').length ?? 0)

function since(iso: string | null): string {
  if (!iso) return ''
  return formatDuration(Math.max(0, Math.floor((now.value - new Date(iso).getTime()) / 1000)))
}

const STATE_LABELS: Record<string, string> = { Up: 'verbunden', Ring: 'klingelt', Ringing: 'klingelt', Down: 'wählt' }

onMounted(() => {
  refresh()
  refreshTimer = setInterval(refresh, REFRESH_MS)
  clockTimer = setInterval(() => { now.value = Date.now() }, 1000)
})
onBeforeUnmount(() => {
  if (refreshTimer) clearInterval(refreshTimer)
  if (clockTimer) clearInterval(clockTimer)
})
</script>

<template>
  <div class="space-y-4">
    <div v-if="failed && !status" class="flex flex-col items-center rounded-2xl border border-line/60 bg-surface py-12 text-center">
      <CircleAlert class="mb-2 h-6 w-6 text-subtle" />
      <p class="text-sm text-muted">Status konnte nicht geladen werden.</p>
    </div>
    <div v-else-if="status?.asterisk_error" class="flex items-start gap-2 rounded-2xl border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-700 dark:text-red-300">
      <CircleAlert class="mt-0.5 h-4 w-4 shrink-0" /> {{ status.asterisk_error }}
    </div>

    <template v-if="status && !status.asterisk_error">
      <!-- Kennzahlen -->
      <div class="grid gap-3 sm:grid-cols-3">
        <div class="rounded-2xl border border-line/60 bg-surface p-4">
          <p class="flex items-center gap-2 text-xs font-medium uppercase tracking-wider text-subtle"><Server class="h-3.5 w-3.5" /> Registriert</p>
          <p class="tabular mt-1 text-2xl font-semibold text-fg">{{ online }}<span class="text-base font-normal text-subtle"> / {{ status.endpoints.length }}</span></p>
        </div>
        <div class="rounded-2xl border border-line/60 bg-surface p-4">
          <p class="flex items-center gap-2 text-xs font-medium uppercase tracking-wider text-subtle"><PhoneCall class="h-3.5 w-3.5" /> Kanäle aktiv</p>
          <p class="tabular mt-1 text-2xl font-semibold text-fg">{{ status.calls.length }}</p>
        </div>
        <div class="rounded-2xl border border-line/60 bg-surface p-4">
          <p class="flex items-center gap-2 text-xs font-medium uppercase tracking-wider text-subtle"><Radio class="h-3.5 w-3.5" /> Sipgate-Trunk</p>
          <p
            class="mt-1 text-lg font-semibold"
            :class="status.trunk_state === 'online' ? 'text-emerald-600 dark:text-emerald-400' : 'text-red-600 dark:text-red-400'"
          >{{ status.trunk_state === 'online' ? 'Online' : status.trunk_state ? 'Offline' : 'Nicht konfiguriert' }}</p>
        </div>
      </div>

      <div class="grid gap-4 lg:grid-cols-2">
        <!-- Geräte -->
        <section class="rounded-2xl border border-line/60 bg-surface">
          <h3 class="border-b border-line/60 px-4 py-3 text-sm font-semibold text-fg">Nebenstellen</h3>
          <ul class="divide-y divide-line/50">
            <li v-for="e in status.endpoints" :key="e.username" class="flex items-center gap-3 px-4 py-2.5">
              <span class="h-2 w-2 shrink-0 rounded-full" :class="e.state === 'online' ? 'bg-emerald-500' : 'bg-line'" />
              <span class="tabular w-10 font-mono text-sm text-fg">{{ e.extension ?? '—' }}</span>
              <span class="min-w-0 flex-1 truncate text-sm text-fg">{{ e.display_name || e.username }}</span>
              <span class="text-xs" :class="e.state === 'online' ? 'text-emerald-600 dark:text-emerald-400' : 'text-subtle'">
                {{ e.state === 'online' ? 'Online' : 'Offline' }}
              </span>
            </li>
            <li v-if="status.endpoints.length === 0" class="px-4 py-6 text-center text-sm text-muted">Keine Nebenstellen.</li>
          </ul>
        </section>

        <!-- Kanäle -->
        <section class="rounded-2xl border border-line/60 bg-surface">
          <h3 class="border-b border-line/60 px-4 py-3 text-sm font-semibold text-fg">Laufende Kanäle</h3>
          <ul class="divide-y divide-line/50">
            <li v-for="c in status.calls" :key="c.channel" class="flex items-center gap-3 px-4 py-2.5">
              <PhoneCall class="h-4 w-4 shrink-0" :class="c.state === 'Up' ? 'text-emerald-500' : 'text-brand'" />
              <div class="min-w-0 flex-1">
                <p class="truncate text-sm text-fg">
                  {{ c.caller_name || c.caller }} <span class="text-subtle">→</span> {{ c.connected ?? '…' }}
                </p>
                <p class="truncate font-mono text-[11px] text-subtle">{{ c.channel }}</p>
              </div>
              <div class="text-right">
                <p class="tabular font-mono text-xs text-fg">{{ since(c.since) }}</p>
                <p class="text-[11px] text-subtle">{{ STATE_LABELS[c.state] ?? c.state }}</p>
              </div>
            </li>
            <li v-if="status.calls.length === 0" class="px-4 py-6 text-center text-sm text-muted">Gerade keine Gespräche.</li>
          </ul>
        </section>
      </div>
      <p class="text-right text-xs text-subtle">Aktualisiert sich alle {{ REFRESH_MS / 1000 }} Sekunden.</p>
    </template>
  </div>
</template>
