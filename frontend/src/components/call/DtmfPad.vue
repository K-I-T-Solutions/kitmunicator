<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { usePhone } from '@/composables/usePhone'
import { DTMF_RE, KEYPAD_KEYS } from '@/lib/keypad'

withDefaults(defineProps<{ compact?: boolean }>(), { compact: false })

const { sendDtmf } = usePhone()
// Gedrückte Töne zur Kontrolle anzeigen (z. B. Mailbox-Menü)
const sent = ref('')

function press(tone: string) {
  sendDtmf(tone)
  sent.value = (sent.value + tone).slice(-24)
}

// Auch über die Tastatur bedienbar, außer beim Tippen in Eingabefeldern
function onKeydown(e: KeyboardEvent) {
  if (e.ctrlKey || e.metaKey || e.altKey || !DTMF_RE.test(e.key)) return
  const target = e.target as HTMLElement | null
  if (target?.closest('input, textarea, [contenteditable="true"]')) return
  e.preventDefault()
  press(e.key)
}
onMounted(() => window.addEventListener('keydown', onKeydown))
onBeforeUnmount(() => window.removeEventListener('keydown', onKeydown))
</script>

<template>
  <div class="w-full">
    <p class="mb-3 h-7 truncate text-center font-mono text-xl tracking-widest text-fg" aria-live="polite">
      {{ sent || ' ' }}
    </p>
    <div class="grid grid-cols-3" :class="compact ? 'gap-1.5' : 'gap-2.5'" role="group" aria-label="Tastenfeld">
      <button
        v-for="k in KEYPAD_KEYS"
        :key="k.d"
        type="button"
        class="flex flex-col items-center justify-center rounded-xl border border-line/60 bg-raised/60 transition-all hover:border-line hover:bg-raised active:scale-95"
        :class="compact ? 'h-11' : 'h-14 md:h-16'"
        :aria-label="`Taste ${k.d}`"
        @click="press(k.d)"
      >
        <span class="font-mono font-medium text-fg" :class="compact ? 'text-lg' : 'text-xl'">{{ k.d }}</span>
        <span v-if="k.l && !compact" class="text-[10px] tracking-widest text-subtle">{{ k.l }}</span>
      </button>
    </div>
  </div>
</template>
