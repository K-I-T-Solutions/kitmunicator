<script setup lang="ts">
import { onBeforeUnmount, watch } from 'vue'
import { CircleAlert, X } from 'lucide-vue-next'
import { usePhoneStore } from '@/stores/phone'

const phone = usePhoneStore()
let timer: ReturnType<typeof setTimeout> | null = null

function dismiss() {
  phone.errorMessage = null
}

// Nach 8 Sekunden automatisch ausblenden
watch(() => phone.errorMessage, (msg) => {
  if (timer) clearTimeout(timer)
  timer = msg ? setTimeout(dismiss, 8000) : null
})
onBeforeUnmount(() => { if (timer) clearTimeout(timer) })
</script>

<template>
  <div
    v-if="phone.errorMessage"
    class="fixed inset-x-4 top-20 z-50 mx-auto flex max-w-md animate-slide-up items-start gap-3 rounded-xl border border-red-500/30 bg-surface p-4 shadow-xl shadow-black/20"
    role="alert"
  >
    <CircleAlert class="mt-0.5 h-5 w-5 shrink-0 text-red-500" />
    <p class="flex-1 text-sm text-fg">{{ phone.errorMessage }}</p>
    <button class="rounded p-0.5 text-subtle hover:text-fg" aria-label="Meldung schließen" @click="dismiss">
      <X class="h-4 w-4" />
    </button>
  </div>
</template>
