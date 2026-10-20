<script setup lang="ts">
import { Phone, PhoneOff } from 'lucide-vue-next'
import { usePhone } from '@/composables/usePhone'
import { useActiveCall } from '@/composables/useActiveCall'
import UserAvatar from '@/components/ui/UserAvatar.vue'

const { remoteNumber, answer, hangup } = usePhone()
const { remoteDisplayName } = useActiveCall()
</script>

<template>
  <!-- Mobil: Vollbild, Desktop: Karte unten rechts -->
  <div
    class="fixed inset-0 z-50 flex animate-fade-in flex-col items-center justify-between bg-app/95 px-8 py-16 backdrop-blur md:inset-auto md:bottom-6 md:right-6 md:block md:w-80 md:animate-slide-in-right md:bg-transparent md:p-0 md:backdrop-blur-none"
    role="alertdialog"
    aria-labelledby="incoming-call-title"
    aria-describedby="incoming-call-caller"
  >
    <div class="contents md:block md:overflow-hidden md:rounded-2xl md:border md:border-line/60 md:bg-surface/95 md:shadow-2xl md:shadow-black/30 md:ring-1 md:ring-cyan-500/20 md:backdrop-blur">
      <div class="contents md:block md:px-5 md:pb-3 md:pt-5">
        <p id="incoming-call-title" class="mt-12 text-sm font-medium uppercase tracking-widest text-brand md:mt-0 md:text-xs">
          Eingehender Anruf
        </p>
        <div id="incoming-call-caller" class="flex flex-col items-center gap-5 md:mt-4 md:flex-row md:gap-4">
          <div class="relative">
            <span class="absolute inset-0 animate-pulse-ring rounded-full bg-cyan-400/30" />
            <UserAvatar :name="remoteDisplayName" size="xl" class="relative ring-4 ring-cyan-400/30 md:hidden" />
            <UserAvatar :name="remoteDisplayName" size="lg" class="relative hidden ring-4 ring-cyan-400/30 md:inline-flex" />
          </div>
          <div class="min-w-0 text-center md:text-left">
            <p class="truncate text-2xl font-semibold text-fg md:text-base">{{ remoteDisplayName }}</p>
            <p v-if="remoteNumber && remoteNumber !== remoteDisplayName" class="mt-1 truncate font-mono text-muted md:mt-0 md:text-sm">
              {{ remoteNumber }}
            </p>
          </div>
        </div>
      </div>

      <div class="flex items-center gap-12 md:justify-between md:gap-0 md:bg-raised/60 md:px-6 md:py-4">
        <button class="flex flex-col items-center gap-2 rounded-xl md:gap-1.5" @click="hangup()">
          <span class="flex h-16 w-16 items-center justify-center rounded-full bg-red-500 text-white shadow-lg shadow-red-500/30 transition-colors hover:bg-red-600 md:h-12 md:w-12">
            <PhoneOff class="h-7 w-7 md:h-5 md:w-5" />
          </span>
          <span class="text-xs text-muted md:text-[11px]">Ablehnen</span>
        </button>
        <button class="flex flex-col items-center gap-2 rounded-xl md:gap-1.5" @click="answer()">
          <span class="flex h-16 w-16 items-center justify-center rounded-full bg-emerald-500 text-white shadow-lg shadow-emerald-500/30 transition-colors hover:bg-emerald-600 md:h-12 md:w-12">
            <Phone class="h-7 w-7 md:h-5 md:w-5" />
          </span>
          <span class="text-xs text-muted md:text-[11px]">Annehmen</span>
        </button>
      </div>
    </div>
  </div>
</template>
