<script setup lang="ts">
import { computed } from 'vue'
import { avatarColor, initials } from '@/lib/format'

const props = withDefaults(defineProps<{
  name: string
  size?: 'sm' | 'md' | 'lg' | 'xl'
}>(), { size: 'md' })

const color = computed(() => avatarColor(props.name))
</script>

<template>
  <span
    class="inline-flex shrink-0 select-none items-center justify-center rounded-full font-semibold text-white"
    :class="{
      'h-8 w-8 text-xs': size === 'sm',
      'h-10 w-10 text-sm': size === 'md',
      'h-12 w-12 text-base': size === 'lg',
      'h-20 w-20 text-2xl': size === 'xl',
    }"
    :style="{ background: `linear-gradient(135deg, ${color}, ${color}cc)` }"
    aria-hidden="true"
  >{{ initials(name) }}</span>
</template>
