<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { Bell, ChevronRight, Eye, LogOut, Music, Play, ShieldCheck, Square, Trash2, Upload, UserRound, Volume2 } from 'lucide-vue-next'
import { RouterLink } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { usePresence, STATUS_LABELS } from '@/composables/usePresence'
import { useTeamVisibility } from '@/composables/useTeamVisibility'
import { useCallNotifications } from '@/composables/useCallNotifications'
import { useRingtone } from '@/composables/useRingtone'
import { RINGTONES, type RingtoneId } from '@/lib/tones'
import UserAvatar from '@/components/ui/UserAvatar.vue'
import GreetingSettings from '@/components/settings/GreetingSettings.vue'

const auth = useAuthStore()
const { team, statuses, loadTeam } = usePresence()
const { isVisible, toggle, setAll } = useTeamVisibility()
const { desktopEnabled, permission, setDesktopEnabled } = useCallNotifications()
const ringtone = useRingtone()

const ringtoneOptions = Object.entries(RINGTONES).map(([id, t]) => ({ id: id as RingtoneId, label: t.label }))
const fileInput = ref<HTMLInputElement | null>(null)
const uploadError = ref<string | null>(null)

async function onFileChosen(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''
  if (!file) return
  ringtone.stopPreview()
  uploadError.value = await ringtone.uploadCustom(file)
}

function chooseRingtone(id: RingtoneId) {
  ringtone.stopPreview()
  ringtone.select(id)
}

onBeforeUnmount(ringtone.stopPreview)

const loading = ref(team.value.length === 0)

const me = computed(() => team.value.find(m => m.user_id === auth.userId))
const colleagues = computed(() => team.value.filter(m => m.user_id !== auth.userId))
const colleagueIds = computed(() => colleagues.value.map(m => m.user_id))
const visibleCount = computed(() => colleagues.value.filter(m => isVisible(m.user_id)).length)

onMounted(async () => {
  await loadTeam()
  loading.value = false
})
</script>

<template>
  <div class="mx-auto max-w-3xl space-y-6 px-4 py-6 md:px-6">
    <!-- Mobil gibt es keinen Navigationseintrag für die Verwaltung -->
    <RouterLink
      v-if="auth.isAdmin"
      to="/admin"
      class="flex items-center gap-3 rounded-2xl border border-cyan-500/30 bg-cyan-500/10 p-4 transition-colors hover:bg-cyan-500/15 md:hidden"
    >
      <ShieldCheck class="h-5 w-5 text-brand" />
      <span class="flex-1 text-sm font-medium text-fg">Verwaltung öffnen</span>
      <ChevronRight class="h-4 w-4 text-brand" />
    </RouterLink>

    <!-- Team-Anzeige -->
    <section class="rounded-2xl border border-line/60 bg-surface p-5 md:p-6" aria-labelledby="team-visibility-title">
      <div class="mb-4 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 id="team-visibility-title" class="flex items-center gap-2 text-sm font-semibold text-fg">
            <Eye class="h-4 w-4 text-brand" /> Team-Anzeige
          </h2>
          <p class="mt-1 text-sm text-muted">Wähle, welche Kollegen auf der Team-Seite angezeigt werden.</p>
        </div>
        <div class="flex gap-2">
          <button
            class="rounded-lg px-3 py-1.5 text-xs font-medium transition-colors"
            :class="visibleCount === colleagues.length ? 'bg-cyan-500/15 text-brand ring-1 ring-cyan-500/25' : 'bg-raised text-muted hover:text-fg'"
            @click="setAll(colleagueIds)"
          >Alle</button>
          <button
            class="rounded-lg px-3 py-1.5 text-xs font-medium transition-colors"
            :class="visibleCount === 0 ? 'bg-cyan-500/15 text-brand ring-1 ring-cyan-500/25' : 'bg-raised text-muted hover:text-fg'"
            @click="setAll([])"
          >Keine</button>
        </div>
      </div>

      <div v-if="loading" class="space-y-2" aria-busy="true">
        <div v-for="i in 3" :key="i" class="h-12 animate-pulse rounded-lg bg-raised" />
      </div>
      <p v-else-if="colleagues.length === 0" class="py-6 text-center text-sm text-muted">
        Noch keine Kollegen mit SIP-Account.
      </p>
      <ul v-else class="divide-y divide-line/50">
        <li v-for="member in colleagues" :key="member.user_id">
          <label class="flex cursor-pointer items-center gap-3 py-2.5">
            <UserAvatar :name="member.username" size="sm" />
            <span class="min-w-0 flex-1">
              <span class="block truncate text-sm text-fg">{{ member.username }}</span>
              <span class="block text-xs text-subtle">
                Durchwahl {{ member.extension }} · {{ STATUS_LABELS[statuses[member.user_id] ?? member.status] }}
              </span>
            </span>
            <input
              type="checkbox"
              role="switch"
              class="peer sr-only"
              :checked="isVisible(member.user_id)"
              @change="toggle(member.user_id, colleagueIds)"
            />
            <!-- Schalter-Optik; der Zustand kommt vom versteckten Checkbox-Input -->
            <span
              class="relative h-6 w-11 shrink-0 rounded-full bg-raised ring-1 ring-line transition-colors peer-checked:bg-cyan-500 peer-checked:ring-cyan-500 peer-focus-visible:outline peer-focus-visible:outline-2 peer-focus-visible:outline-offset-2 peer-focus-visible:outline-cyan-500 peer-checked:[&>span]:translate-x-5"
              aria-hidden="true"
            >
              <span class="absolute left-0.5 top-0.5 h-5 w-5 rounded-full bg-white shadow transition-transform" />
            </span>
          </label>
        </li>
      </ul>
    </section>

    <GreetingSettings id="ansage" class="scroll-mt-6" />

    <!-- Klingelton -->
    <section class="rounded-2xl border border-line/60 bg-surface p-5 md:p-6" aria-labelledby="ringtone-title">
      <div class="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 id="ringtone-title" class="flex items-center gap-2 text-sm font-semibold text-fg">
            <Music class="h-4 w-4 text-brand" /> Klingelton
          </h2>
          <p class="mt-1 text-sm text-muted">Gilt für diesen Browser – jedes Gerät kann anders klingeln.</p>
        </div>
        <button
          class="inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium ring-1 transition-colors"
          :class="ringtone.previewing.value ? 'bg-cyan-500 text-navy-800 ring-cyan-500' : 'bg-cyan-500/15 text-brand ring-cyan-500/25 hover:bg-cyan-500/25'"
          @click="ringtone.togglePreview()"
        >
          <Square v-if="ringtone.previewing.value" class="h-3.5 w-3.5" />
          <Play v-else class="h-3.5 w-3.5" />
          {{ ringtone.previewing.value ? 'Stopp' : 'Anhören' }}
        </button>
      </div>

      <div class="mt-4 grid grid-cols-2 gap-2 sm:grid-cols-4" role="radiogroup" aria-label="Klingelton">
        <button
          v-for="option in ringtoneOptions"
          :key="option.id"
          role="radio"
          :aria-checked="ringtone.prefs.value.id === option.id"
          class="rounded-xl px-3 py-2.5 text-sm font-medium transition-colors"
          :class="ringtone.prefs.value.id === option.id
            ? 'bg-cyan-500/10 text-brand ring-1 ring-cyan-500/40'
            : 'bg-raised text-muted ring-1 ring-transparent hover:text-fg'"
          @click="chooseRingtone(option.id)"
        >{{ option.label }}</button>
      </div>

      <!-- Eigene Datei -->
      <div
        class="mt-2 flex items-center gap-3 rounded-xl px-3 py-2.5 ring-1 transition-colors"
        :class="ringtone.prefs.value.id === 'custom' ? 'bg-cyan-500/10 ring-cyan-500/40' : 'bg-raised ring-transparent'"
      >
        <button
          v-if="ringtone.prefs.value.customName"
          role="radio"
          :aria-checked="ringtone.prefs.value.id === 'custom'"
          class="min-w-0 flex-1 truncate text-left text-sm font-medium"
          :class="ringtone.prefs.value.id === 'custom' ? 'text-brand' : 'text-muted hover:text-fg'"
          :title="ringtone.prefs.value.customName"
          @click="chooseRingtone('custom')"
        >Eigene: {{ ringtone.prefs.value.customName }}</button>
        <span v-else class="min-w-0 flex-1 text-sm text-muted">Eigene Datei (MP3, WAV, OGG · max. 5 MB)</span>
        <button
          class="inline-flex shrink-0 items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-xs font-medium text-brand transition-colors hover:bg-cyan-500/10"
          @click="fileInput?.click()"
        >
          <Upload class="h-3.5 w-3.5" /> {{ ringtone.prefs.value.customName ? 'Ersetzen' : 'Hochladen' }}
        </button>
        <button
          v-if="ringtone.prefs.value.customName"
          class="shrink-0 rounded-lg p-1.5 text-subtle transition-colors hover:bg-red-500/10 hover:text-red-500"
          aria-label="Eigenen Klingelton entfernen"
          title="Entfernen"
          @click="ringtone.stopPreview(); ringtone.removeCustom()"
        >
          <Trash2 class="h-3.5 w-3.5" />
        </button>
        <input ref="fileInput" type="file" accept="audio/*" class="hidden" @change="onFileChosen" />
      </div>
      <p v-if="uploadError" class="mt-2 text-xs text-red-600 dark:text-red-400">{{ uploadError }}</p>

      <label class="mt-4 flex items-center gap-3">
        <Volume2 class="h-4 w-4 shrink-0 text-subtle" />
        <span class="sr-only">Lautstärke</span>
        <input
          type="range"
          min="0.05"
          max="1"
          step="0.05"
          class="h-1.5 flex-1 cursor-pointer accent-cyan-500"
          :value="ringtone.prefs.value.volume"
          @input="ringtone.setVolume(Number(($event.target as HTMLInputElement).value))"
        />
        <span class="tabular w-10 text-right font-mono text-xs text-subtle">{{ Math.round(ringtone.prefs.value.volume * 100) }} %</span>
      </label>
    </section>

    <!-- Benachrichtigungen -->
    <section class="rounded-2xl border border-line/60 bg-surface p-5 md:p-6" aria-labelledby="notify-title">
      <h2 id="notify-title" class="flex items-center gap-2 text-sm font-semibold text-fg">
        <Bell class="h-4 w-4 text-brand" /> Benachrichtigungen
      </h2>
      <p class="mt-1 text-sm text-muted">
        Verpasste Anrufe und neue Voicemails erscheinen in der App. Ist der Tab im Hintergrund,
        kann zusätzlich eine Desktop-Benachrichtigung kommen.
      </p>
      <label class="mt-4 flex items-center gap-3" :class="permission === 'granted' || permission === 'default' ? 'cursor-pointer' : 'opacity-60'">
        <span class="min-w-0 flex-1">
          <span class="block text-sm text-fg">Desktop-Benachrichtigungen</span>
          <span class="block text-xs text-subtle">
            <template v-if="permission === 'unsupported'">Von diesem Browser nicht unterstützt.</template>
            <template v-else-if="permission === 'denied'">Im Browser blockiert – in den Website-Einstellungen freigeben.</template>
            <template v-else-if="permission === 'default'">Beim Einschalten fragt der Browser nach.</template>
            <template v-else>Nur wenn der Tab im Hintergrund ist.</template>
          </span>
        </span>
        <input
          type="checkbox"
          role="switch"
          class="peer sr-only"
          :checked="desktopEnabled && permission === 'granted'"
          :disabled="permission === 'denied' || permission === 'unsupported'"
          @change="setDesktopEnabled(($event.target as HTMLInputElement).checked)"
        />
        <span
          class="relative h-6 w-11 shrink-0 rounded-full bg-raised ring-1 ring-line transition-colors peer-checked:bg-cyan-500 peer-checked:ring-cyan-500 peer-focus-visible:outline peer-focus-visible:outline-2 peer-focus-visible:outline-offset-2 peer-focus-visible:outline-cyan-500 peer-checked:[&>span]:translate-x-5"
          aria-hidden="true"
        >
          <span class="absolute left-0.5 top-0.5 h-5 w-5 rounded-full bg-white shadow transition-transform" />
        </span>
      </label>
    </section>

    <!-- Konto -->
    <section class="rounded-2xl border border-line/60 bg-surface p-5 md:p-6" aria-labelledby="account-title">
      <h2 id="account-title" class="mb-4 flex items-center gap-2 text-sm font-semibold text-fg">
        <UserRound class="h-4 w-4 text-brand" /> Konto
      </h2>
      <dl class="grid gap-3 text-sm sm:grid-cols-[10rem_1fr]">
        <dt class="text-muted">Name</dt>
        <dd class="text-fg">{{ auth.displayName }}</dd>
        <dt class="text-muted">SIP-Benutzer</dt>
        <dd class="font-mono text-fg">{{ me?.username ?? '—' }}</dd>
        <dt class="text-muted">Durchwahl</dt>
        <dd class="font-mono text-fg">{{ me?.extension ?? '—' }}</dd>
      </dl>
      <button
        class="mt-5 inline-flex items-center gap-2 rounded-lg border border-line px-3.5 py-2 text-sm font-medium text-fg transition-colors hover:border-red-500/40 hover:bg-red-500/10 hover:text-red-600 dark:hover:text-red-400"
        @click="auth.logout()"
      >
        <LogOut class="h-4 w-4" /> Abmelden
      </button>
    </section>
  </div>
</template>
