<script setup lang="ts">
import { onBeforeUnmount, ref, watch } from 'vue'
import { Check, ChevronDown } from 'lucide-vue-next'
import { STATUS_LABELS, type PresenceStatus } from '@/composables/usePresence'
import PresenceDot from './PresenceDot.vue'

const props = defineProps<{ modelValue: PresenceStatus }>()
const emit = defineEmits<{ 'update:modelValue': [status: PresenceStatus] }>()

const OPTIONS: PresenceStatus[] = ['available', 'busy', 'away', 'dnd']

const open = ref(false)
const root = ref<HTMLElement | null>(null)

function select(status: PresenceStatus) {
  open.value = false
  if (status !== props.modelValue) emit('update:modelValue', status)
}

function onPointerDown(e: PointerEvent) {
  if (root.value && !root.value.contains(e.target as Node)) open.value = false
}
function onKeydown(e: KeyboardEvent) {
  if (e.key === 'Escape') open.value = false
}

watch(open, (isOpen) => {
  if (isOpen) {
    document.addEventListener('pointerdown', onPointerDown)
    document.addEventListener('keydown', onKeydown)
  } else {
    document.removeEventListener('pointerdown', onPointerDown)
    document.removeEventListener('keydown', onKeydown)
  }
})
onBeforeUnmount(() => { open.value = false })
</script>

<template>
  <div ref="root" class="relative">
    <button
      class="flex items-center gap-2.5 rounded-xl border border-line bg-raised/60 px-4 py-2.5 text-sm font-medium text-fg transition-colors hover:border-subtle"
      aria-haspopup="listbox"
      :aria-expanded="open"
      @click="open = !open"
    >
      <PresenceDot :status="modelValue" size="xs" class="ring-0" />
      {{ STATUS_LABELS[modelValue] }}
      <ChevronDown class="h-4 w-4 text-muted transition-transform" :class="{ 'rotate-180': open }" />
    </button>

    <ul
      v-if="open"
      class="absolute right-0 z-20 mt-2 w-52 animate-slide-up rounded-xl border border-line bg-surface py-1.5 shadow-xl shadow-black/20"
      role="listbox"
      aria-label="Status wählen"
    >
      <li v-for="option in OPTIONS" :key="option">
        <button
          class="flex w-full items-center gap-3 px-4 py-2.5 text-sm text-fg transition-colors hover:bg-raised"
          role="option"
          :aria-selected="option === modelValue"
          @click="select(option)"
        >
          <PresenceDot :status="option" size="xs" class="ring-0" />
          {{ STATUS_LABELS[option] }}
          <Check v-if="option === modelValue" class="ml-auto h-4 w-4 text-brand" />
        </button>
      </li>
    </ul>
  </div>
</template>
