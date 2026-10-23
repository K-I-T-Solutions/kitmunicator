<script setup lang="ts">
import { Mic, MicOff, Pause, Phone, PhoneOff, Play } from 'lucide-vue-next'
import { usePhone } from '@/composables/usePhone'
import { useActiveCall } from '@/composables/useActiveCall'
import { formatDuration } from '@/lib/format'

const { callState, remoteNumber, isMuted, isOnHold, callDurationSeconds, hangup, mute, hold } = usePhone()
const { remoteDisplayName, callStatusLabel, calleeNotice } = useActiveCall()
</script>

<template>
  <div class="fixed inset-x-0 bottom-[calc(4rem+env(safe-area-inset-bottom))] z-40 animate-slide-up md:bottom-4 md:left-1/2 md:right-auto md:-translate-x-1/2">
    <div
      class="flex items-center gap-3 border-t border-line/60 bg-surface/95 px-4 py-3 shadow-2xl shadow-black/30 ring-1 ring-cyan-500/20 backdrop-blur md:w-[480px] md:rounded-2xl md:border"
      role="region"
      aria-label="Laufender Anruf"
    >
      <div class="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-cyan-500/15 ring-1 ring-cyan-500/30">
        <Phone class="h-4 w-4 text-brand" />
      </div>
      <div class="min-w-0 flex-1">
        <p class="truncate text-sm font-medium text-fg">{{ remoteDisplayName }}</p>
        <p v-if="calleeNotice" class="truncate text-xs text-amber-400" role="status">{{ calleeNotice }}</p>
        <p v-else-if="remoteNumber && remoteNumber !== remoteDisplayName" class="truncate font-mono text-xs text-muted">{{ remoteNumber }}</p>
      </div>
      <div class="shrink-0 text-right">
        <p class="text-[11px] font-medium uppercase tracking-wide text-brand">{{ callStatusLabel }}</p>
        <p v-if="callState === 'connected'" class="tabular font-mono text-sm text-fg">{{ formatDuration(callDurationSeconds) }}</p>
      </div>
      <div class="flex shrink-0 items-center gap-1.5 pl-1">
        <button
          class="flex h-9 w-9 items-center justify-center rounded-full transition-colors disabled:opacity-40"
          :class="isMuted ? 'bg-accent-500 text-white' : 'bg-raised text-muted hover:text-fg'"
          :aria-label="isMuted ? 'Stummschaltung aufheben' : 'Stummschalten'"
          :aria-pressed="isMuted"
          :disabled="callState !== 'connected'"
          @click="mute()"
        >
          <MicOff v-if="isMuted" class="h-4 w-4" />
          <Mic v-else class="h-4 w-4" />
        </button>
        <button
          class="flex h-9 w-9 items-center justify-center rounded-full transition-colors disabled:opacity-40"
          :class="isOnHold ? 'bg-amber-500 text-white' : 'bg-raised text-muted hover:text-fg'"
          :aria-label="isOnHold ? 'Fortsetzen' : 'Halten'"
          :aria-pressed="isOnHold"
          :disabled="callState !== 'connected'"
          @click="hold()"
        >
          <Play v-if="isOnHold" class="h-4 w-4" />
          <Pause v-else class="h-4 w-4" />
        </button>
        <button
          class="flex h-9 w-9 items-center justify-center rounded-full bg-red-500 text-white transition-colors hover:bg-red-600"
          aria-label="Auflegen"
          @click="hangup()"
        >
          <PhoneOff class="h-4 w-4" />
        </button>
      </div>
    </div>
  </div>
</template>
