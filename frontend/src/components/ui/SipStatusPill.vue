<script setup lang="ts">
import type { SipState } from '@/composables/useActiveCall'

defineProps<{ state: SipState }>()
</script>

<template>
  <span
    v-if="state === 'connecting'"
    class="inline-flex items-center gap-2 rounded-full bg-amber-500/10 px-3 py-1.5 text-xs font-medium text-amber-600 ring-1 ring-amber-500/25 dark:text-amber-400"
  >
    <span class="h-2 w-2 animate-pulse-soft rounded-full bg-amber-500" />
    Verbinde…
  </span>
  <span
    v-else-if="state === 'error'"
    class="inline-flex cursor-help items-center gap-2 rounded-full bg-red-500/10 px-3 py-1.5 text-xs font-medium text-red-600 ring-1 ring-red-500/25 dark:text-red-400"
    title="Verbindung zum SIP-Server fehlgeschlagen"
  >
    <span class="h-2 w-2 rounded-full bg-red-500" />
    Fehler
  </span>
  <span
    v-else-if="state === 'offline'"
    class="inline-flex items-center gap-2 rounded-full bg-raised px-3 py-1.5 text-xs font-medium text-muted ring-1 ring-line"
    title="Telefon ist nicht beim SIP-Server angemeldet"
  >
    <span class="h-2 w-2 rounded-full bg-presence-offline" />
    Nicht verbunden
  </span>
  <span
    v-else
    class="inline-flex items-center gap-2 rounded-full bg-emerald-500/10 px-3 py-1.5 text-xs font-medium text-emerald-700 ring-1 ring-emerald-500/25 dark:text-emerald-400"
  >
    <span class="h-2 w-2 rounded-full bg-emerald-500" />
    Registriert
  </span>
</template>
