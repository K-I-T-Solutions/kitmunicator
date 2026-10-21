<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { CircleAlert, Inbox, Loader2, MailOpen, Pause, Phone, Play, RefreshCw } from 'lucide-vue-next'
import { useAuthStore } from '@/stores/auth'
import { usePhone } from '@/composables/usePhone'
import { usePresence } from '@/composables/usePresence'
import { useVoicemail, type Voicemail } from '@/composables/useVoicemail'
import { formatCallTime, formatDuration } from '@/lib/format'
import UserAvatar from '@/components/ui/UserAvatar.vue'

const auth = useAuthStore()
const { isBusy, call } = usePhone()
const { team, memberByExtension } = usePresence()
const { messages, loadState, unreadCount, load, markRead, fetchAudio } = useVoicemail()

const myExtension = computed(() => team.value.find(m => m.user_id === auth.userId)?.extension)

/** Kollegen per Durchwahl auflösen, sonst Caller-ID-Name aus Asterisk */
function callerName(vm: Voicemail): string | null {
  return memberByExtension(vm.caller_number)?.username ?? vm.caller_name
}
function isDialable(vm: Voicemail): boolean {
  return /^[+\d*#]+$/.test(vm.caller_number)
}

const refreshing = ref(false)
async function refresh() {
  refreshing.value = true
  await load()
  refreshing.value = false
}

onMounted(load)

// ── Wiedergabe: ein Player für alle Nachrichten ─────────────────────────────

const audio = new Audio()
const activeId = ref<number | null>(null)
const loadingId = ref<number | null>(null)
const playing = ref(false)
const position = ref(0)
const audioError = ref<number | null>(null)
const blobUrls = new Map<number, string>()

audio.addEventListener('timeupdate', () => { position.value = audio.currentTime })
audio.addEventListener('play', () => { playing.value = true })
audio.addEventListener('pause', () => { playing.value = false })
audio.addEventListener('ended', () => { position.value = 0 })

async function toggle(vm: Voicemail) {
  if (activeId.value === vm.id) {
    if (audio.paused) await audio.play()
    else audio.pause()
    return
  }

  audio.pause()
  audioError.value = null
  loadingId.value = vm.id
  try {
    let url = blobUrls.get(vm.id)
    if (!url) {
      url = await fetchAudio(vm.id)
      blobUrls.set(vm.id, url)
    }
    activeId.value = vm.id
    position.value = 0
    audio.src = url
    await audio.play()
    markRead(vm.id)
  } catch {
    audioError.value = vm.id
  } finally {
    loadingId.value = null
  }
}

function seek(vm: Voicemail, event: Event) {
  if (activeId.value !== vm.id) return
  audio.currentTime = Number((event.target as HTMLInputElement).value)
}

function remaining(vm: Voicemail): string {
  const elapsed = activeId.value === vm.id ? Math.floor(position.value) : 0
  return formatDuration(Math.max(0, vm.duration_seconds - elapsed))
}

onBeforeUnmount(() => {
  audio.pause()
  blobUrls.forEach(url => URL.revokeObjectURL(url))
})
</script>

<template>
  <div class="mx-auto max-w-3xl px-4 py-6 md:px-6">
    <div class="mb-4 flex items-center justify-between gap-3">
      <div>
        <h2 class="text-sm font-semibold text-fg">
          {{ messages.length }} {{ messages.length === 1 ? 'Nachricht' : 'Nachrichten' }}
          <span v-if="unreadCount" class="font-normal text-muted">· {{ unreadCount }} neu</span>
        </h2>
        <p v-if="myExtension" class="mt-0.5 text-xs text-subtle">
          Am Telefon abhören: <span class="font-mono">*98{{ myExtension }}</span>
        </p>
      </div>
      <button
        class="rounded-lg p-2 text-muted transition-colors hover:bg-raised hover:text-fg disabled:opacity-40"
        :disabled="refreshing"
        aria-label="Aktualisieren"
        title="Aktualisieren"
        @click="refresh"
      >
        <RefreshCw class="h-4 w-4" :class="refreshing && 'animate-spin'" />
      </button>
    </div>

    <div v-if="loadState === 'loading' || loadState === 'idle'" class="space-y-3" aria-busy="true">
      <div v-for="n in 3" :key="n" class="h-32 animate-pulse rounded-2xl border border-line/60 bg-surface" />
    </div>

    <div v-else-if="loadState === 'error' && messages.length === 0" class="flex flex-col items-center py-20 text-center">
      <CircleAlert class="mb-2 h-6 w-6 text-subtle" />
      <p class="text-sm text-muted">Sprachnachrichten konnten nicht geladen werden.</p>
      <button class="mt-2 text-sm text-brand hover:underline" @click="refresh">Erneut versuchen</button>
    </div>

    <div v-else-if="messages.length === 0" class="flex flex-col items-center py-20 text-center">
      <span class="mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-raised text-subtle">
        <Inbox class="h-6 w-6" />
      </span>
      <p class="text-sm text-muted">Keine Sprachnachrichten</p>
      <p class="mt-1 text-xs text-subtle">Wer dich nicht erreicht, kann nach 30 Sekunden eine Nachricht hinterlassen.</p>
    </div>

    <ul v-else class="space-y-3">
      <li
        v-for="vm in messages"
        :key="vm.id"
        class="rounded-2xl border bg-surface p-4 transition-colors"
        :class="vm.is_read ? 'border-line/60' : 'border-accent-500/40'"
      >
        <div class="flex items-center gap-3">
          <div class="relative">
            <UserAvatar :name="callerName(vm) || vm.caller_number" />
            <span
              v-if="!vm.is_read"
              class="absolute -right-0.5 -top-0.5 h-3 w-3 rounded-full bg-accent-500 ring-2 ring-surface"
              title="Neu"
            />
          </div>
          <div class="min-w-0 flex-1">
            <p class="truncate text-sm text-fg" :class="vm.is_read ? 'font-medium' : 'font-semibold'">
              {{ callerName(vm) || vm.caller_number }}
            </p>
            <p class="tabular truncate text-xs text-subtle">
              <span v-if="callerName(vm)" class="font-mono">{{ vm.caller_number }} · </span>{{ formatCallTime(vm.received_at) }}
            </p>
          </div>
        </div>

        <div class="mt-3 flex items-center gap-3">
          <button
            class="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-cyan-500/15 text-brand ring-1 ring-cyan-500/25 transition-colors hover:bg-cyan-500/25"
            :aria-label="activeId === vm.id && playing ? 'Pause' : 'Abspielen'"
            @click="toggle(vm)"
          >
            <Loader2 v-if="loadingId === vm.id" class="h-4 w-4 animate-spin" />
            <Pause v-else-if="activeId === vm.id && playing" class="h-4 w-4" />
            <Play v-else class="ml-0.5 h-4 w-4" />
          </button>
          <input
            type="range"
            class="h-1.5 flex-1 cursor-pointer accent-cyan-500 disabled:cursor-default"
            min="0"
            step="0.1"
            :max="vm.duration_seconds"
            :value="activeId === vm.id ? position : 0"
            :disabled="activeId !== vm.id"
            :aria-label="`Position in der Nachricht von ${callerName(vm) || vm.caller_number}`"
            @input="seek(vm, $event)"
          >
          <span class="tabular w-11 shrink-0 text-right font-mono text-xs text-subtle">{{ remaining(vm) }}</span>
        </div>
        <p v-if="audioError === vm.id" class="mt-2 text-xs text-red-600 dark:text-red-400">
          Audiodatei konnte nicht geladen werden.
        </p>

        <div class="mt-3 flex flex-wrap items-center gap-2 border-t border-line/40 pt-3">
          <button
            v-if="!vm.is_read"
            class="flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium text-muted transition-colors hover:bg-raised hover:text-fg"
            @click="markRead(vm.id)"
          >
            <MailOpen class="h-3.5 w-3.5" />
            Als gelesen markieren
          </button>
          <button
            v-if="isDialable(vm)"
            class="flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium text-brand transition-colors hover:bg-cyan-500/10 disabled:opacity-40"
            :disabled="isBusy"
            @click="call(vm.caller_number, callerName(vm) ?? undefined)"
          >
            <Phone class="h-3.5 w-3.5" />
            Zurückrufen
          </button>
        </div>
      </li>
    </ul>
  </div>
</template>
