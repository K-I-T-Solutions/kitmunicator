<script setup lang="ts">
import { PhoneMissed, Phone, Play, Voicemail, X } from 'lucide-vue-next'
import { usePhone } from '@/composables/usePhone'
import { useCallNotifications, noticeSuffix, type CallNotice } from '@/composables/useCallNotifications'
import { formatCallTime } from '@/lib/format'
import UserAvatar from '@/components/ui/UserAvatar.vue'

const { isBusy, call } = usePhone()
const { notices, dismiss, openVoicemail } = useCallNotifications()

function callBack(notice: CallNotice) {
  dismiss(notice.id)
  call(notice.caller_number, notice.name !== notice.caller_number ? notice.name : undefined)
}
</script>

<template>
  <!-- Oben rechts, unter der Kopfzeile; mobil über die volle Breite -->
  <div class="pointer-events-none fixed inset-x-4 top-20 z-40 flex flex-col items-end gap-3 md:left-auto md:right-6 md:w-96" aria-live="polite">
    <div
      v-for="notice in notices"
      :key="notice.id"
      class="pointer-events-auto w-full animate-slide-in-right overflow-hidden rounded-2xl border bg-surface/95 shadow-xl shadow-black/20 backdrop-blur"
      :class="notice.voicemail_id ? 'border-accent-500/40' : 'border-line/60'"
      role="status"
    >
      <div class="flex items-start gap-3 p-4">
        <div class="relative">
          <UserAvatar :name="notice.name" />
          <span
            class="absolute -bottom-1 -right-1 flex h-5 w-5 items-center justify-center rounded-full ring-2 ring-surface"
            :class="notice.voicemail_id ? 'bg-accent-500 text-white' : 'bg-red-500 text-white'"
          >
            <Voicemail v-if="notice.voicemail_id" class="h-3 w-3" />
            <PhoneMissed v-else class="h-3 w-3" />
          </span>
        </div>
        <div class="min-w-0 flex-1">
          <p class="text-sm text-fg">
            <span class="font-semibold">{{ notice.name }}</span>
            {{ noticeSuffix(notice) }}
          </p>
          <p class="tabular mt-0.5 text-xs text-subtle">
            <template v-if="notice.name !== notice.caller_number"><span class="font-mono">{{ notice.caller_number }}</span> · </template>{{ formatCallTime(notice.at) }}
          </p>
        </div>
        <button class="rounded p-0.5 text-subtle hover:text-fg" aria-label="Benachrichtigung schließen" @click="dismiss(notice.id)">
          <X class="h-4 w-4" />
        </button>
      </div>
      <div class="flex gap-2 border-t border-line/40 bg-raised/40 px-4 py-2.5">
        <button
          v-if="notice.voicemail_id"
          class="flex items-center gap-1.5 rounded-lg bg-cyan-500/15 px-3 py-1.5 text-xs font-medium text-brand ring-1 ring-cyan-500/25 transition-colors hover:bg-cyan-500/25"
          @click="openVoicemail(notice)"
        >
          <Play class="h-3.5 w-3.5" /> Anhören
        </button>
        <button
          class="flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium text-brand transition-colors hover:bg-cyan-500/10 disabled:opacity-40"
          :disabled="isBusy"
          @click="callBack(notice)"
        >
          <Phone class="h-3.5 w-3.5" /> Zurückrufen
        </button>
      </div>
    </div>
  </div>
</template>
