<script setup lang="ts">
import { Contact } from 'lucide-vue-next'
</script>

<template>
  <div class="mx-auto max-w-3xl px-4 py-6 md:px-6">
    <div class="flex flex-col items-center justify-center rounded-2xl border border-dashed border-line py-16 text-center">
      <span class="mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-raised text-subtle">
        <Contact class="h-6 w-6" />
      </span>
      <p class="text-sm text-fg">Kontaktverwaltung folgt.</p>
    </div>
  </div>
</template>
