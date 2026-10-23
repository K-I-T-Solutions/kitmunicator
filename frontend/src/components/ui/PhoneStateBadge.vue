<script setup lang="ts">
import type { PhoneStatus } from '@/composables/usePresence'

defineProps<{ state: PhoneStatus }>()
</script>

<template>
  <span v-if="state === 'ringing'" class="inline-flex items-center gap-1.5 text-xs font-medium text-brand">
    <span class="relative flex h-2 w-2">
      <span class="absolute inline-flex h-full w-full animate-pulse-ring rounded-full bg-cyan-400 opacity-75" />
      <span class="relative inline-flex h-2 w-2 rounded-full bg-cyan-400" />
    </span>
    Klingelt
  </span>
  <span v-else-if="state === 'in_call'" class="inline-flex items-center gap-1.5 text-xs font-medium text-red-600 dark:text-red-400">
    <span class="h-2 w-2 rounded-full bg-red-500" />
    Im Gespräch
  </span>
  <span v-else-if="state === 'offline'" class="text-xs text-subtle">Telefon offline</span>
</template>
