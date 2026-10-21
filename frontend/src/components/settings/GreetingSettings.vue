<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { Check, Mic, Pause, Play, RotateCcw, Square, Upload, Voicemail, X } from 'lucide-vue-next'
import { usePhone } from '@/composables/usePhone'
import { useGreeting, GREETING_MAX_SECONDS } from '@/composables/useGreeting'
import { formatCallTime, formatDuration } from '@/lib/format'

const { isBusy } = usePhone()
const greeting = useGreeting()
const { status, recording, recordSeconds, draft, busy, error } = greeting

const fileInput = ref<HTMLInputElement | null>(null)

// ── Wiedergabe: Entwurf oder gespeicherte Ansage ───────────────────────────
const audio = new Audio()
const playing = ref<'draft' | 'saved' | null>(null)
let savedUrl: string | null = null
audio.addEventListener('ended', () => { playing.value = null })
audio.addEventListener('pause', () => { playing.value = null })

async function togglePlay(which: 'draft' | 'saved') {
  if (playing.value === which) return audio.pause()
  audio.pause()
  try {
    if (which === 'draft') {
      if (!draft.value) return
      audio.src = draft.value.url
    } else {
      savedUrl ??= await greeting.fetchSavedUrl()
      audio.src = savedUrl
    }
    await audio.play()
    playing.value = which
  } catch {
    error.value = 'Abspielen fehlgeschlagen.'
  }
}

function forgetSavedAudio() {
  audio.pause()
  if (savedUrl) URL.revokeObjectURL(savedUrl)
  savedUrl = null
}

async function onFileChosen(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''
  if (file) await greeting.useAudio(file)
}

async function save() {
  audio.pause()
  await greeting.save()
  forgetSavedAudio()
}

async function resetToDefault() {
  forgetSavedAudio()
  await greeting.remove()
}

function startRecording() {
  audio.pause()
  greeting.startRecording()
}

onMounted(greeting.load)
onBeforeUnmount(() => {
  forgetSavedAudio()
  greeting.dispose()
})
</script>

<template>
  <section class="rounded-2xl border border-line/60 bg-surface p-5 md:p-6" aria-labelledby="greeting-title">
    <h2 id="greeting-title" class="flex items-center gap-2 text-sm font-semibold text-fg">
      <Voicemail class="h-4 w-4 text-brand" /> Voicemail-Ansage
    </h2>
    <p class="mt-1 text-sm text-muted">
      Das hören Anrufer, wenn du nicht rangehst. Danach kommt der Piepton und die Aufnahme startet.
    </p>

    <!-- Aktueller Stand -->
    <div class="mt-4 flex flex-wrap items-center gap-3 rounded-xl bg-raised px-4 py-3">
      <div class="min-w-0 flex-1">
        <template v-if="status?.exists">
          <p class="text-sm font-medium text-fg">Eigene Ansage · {{ formatDuration(status.duration_seconds ?? 0) }}</p>
          <p v-if="status.updated_at" class="text-xs text-subtle">Aufgenommen {{ formatCallTime(status.updated_at) }}</p>
        </template>
        <template v-else>
          <p class="text-sm font-medium text-fg">Standardansage</p>
          <p class="text-xs text-subtle">„Der Teilnehmer … ist nicht erreichbar“</p>
        </template>
      </div>
      <template v-if="status?.exists">
        <button
          class="inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium text-brand transition-colors hover:bg-cyan-500/10"
          @click="togglePlay('saved')"
        >
          <Pause v-if="playing === 'saved'" class="h-3.5 w-3.5" />
          <Play v-else class="h-3.5 w-3.5" />
          Anhören
        </button>
        <button
          class="inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium text-muted transition-colors hover:bg-red-500/10 hover:text-red-600 disabled:opacity-40 dark:hover:text-red-400"
          :disabled="busy"
          @click="resetToDefault"
        >
          <RotateCcw class="h-3.5 w-3.5" /> Standard verwenden
        </button>
      </template>
    </div>

    <!-- Entwurf prüfen -->
    <div v-if="draft" class="mt-3 flex flex-wrap items-center gap-3 rounded-xl px-4 py-3 ring-1 ring-cyan-500/40">
      <button
        class="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-cyan-500/15 text-brand ring-1 ring-cyan-500/25 hover:bg-cyan-500/25"
        :aria-label="playing === 'draft' ? 'Pause' : 'Neue Ansage anhören'"
        @click="togglePlay('draft')"
      >
        <Pause v-if="playing === 'draft'" class="h-4 w-4" />
        <Play v-else class="ml-0.5 h-4 w-4" />
      </button>
      <p class="min-w-0 flex-1 text-sm text-fg">
        Neue Ansage · <span class="tabular font-mono">{{ formatDuration(Math.round(draft.seconds)) }}</span>
        <span class="block text-xs text-subtle">Erst anhören, dann speichern.</span>
      </p>
      <button
        class="inline-flex items-center gap-1.5 rounded-lg bg-cyan-500 px-3 py-1.5 text-xs font-semibold text-navy-800 transition-colors hover:bg-cyan-400 disabled:opacity-40"
        :disabled="busy"
        @click="save"
      >
        <Check class="h-3.5 w-3.5" /> Speichern
      </button>
      <button
        class="inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium text-muted transition-colors hover:bg-raised hover:text-fg"
        @click="audio.pause(); greeting.discardDraft()"
      >
        <X class="h-3.5 w-3.5" /> Verwerfen
      </button>
    </div>

    <!-- Aufnehmen / Hochladen -->
    <div class="mt-3 flex flex-wrap items-center gap-2">
      <button
        v-if="!recording"
        class="inline-flex items-center gap-2 rounded-lg border border-line px-3.5 py-2 text-sm font-medium text-fg transition-colors hover:border-red-500/40 hover:bg-red-500/10 disabled:opacity-40"
        :disabled="busy || isBusy"
        :title="isBusy ? 'Während eines Gesprächs nicht möglich' : undefined"
        @click="startRecording"
      >
        <Mic class="h-4 w-4 text-red-500" /> {{ status?.exists || draft ? 'Neu aufnehmen' : 'Aufnehmen' }}
      </button>
      <button
        v-else
        class="inline-flex items-center gap-2 rounded-lg bg-red-500 px-3.5 py-2 text-sm font-semibold text-white transition-colors hover:bg-red-600"
        @click="greeting.stopRecording()"
      >
        <span class="h-2 w-2 animate-pulse rounded-full bg-white" />
        <Square class="h-3.5 w-3.5" /> Stopp
        <span class="tabular font-mono text-xs font-normal opacity-90">
          {{ formatDuration(recordSeconds) }} / {{ formatDuration(GREETING_MAX_SECONDS) }}
        </span>
      </button>
      <button
        class="inline-flex items-center gap-2 rounded-lg px-3.5 py-2 text-sm font-medium text-brand transition-colors hover:bg-cyan-500/10 disabled:opacity-40"
        :disabled="busy || recording"
        @click="fileInput?.click()"
      >
        <Upload class="h-4 w-4" /> Datei hochladen
      </button>
      <input ref="fileInput" type="file" accept="audio/*" class="hidden" @change="onFileChosen" />
    </div>

    <p v-if="error" class="mt-2 text-xs text-red-600 dark:text-red-400">{{ error }}</p>
    <p v-else class="mt-3 text-xs text-subtle">
      Zum Beispiel: „Hallo, hier ist … von K.I.T. Solutions. Ich bin gerade nicht erreichbar –
      hinterlass mir nach dem Piepton eine Nachricht, ich rufe zurück.“
    </p>
  </section>
</template>
