<script setup lang="ts">
import { computed } from 'vue'
import { STATUS_LABELS, type PresenceStatus } from '@/composables/usePresence'

const props = withDefaults(defineProps<{
  status: PresenceStatus | 'offline'
  size?: 'xs' | 'sm'
}>(), { size: 'sm' })

const label = computed(() => props.status === 'offline' ? 'Offline' : STATUS_LABELS[props.status])
</script>

<template>
  <span
    class="inline-block rounded-full ring-2 ring-surface"
    :class="[
      size === 'xs' ? 'h-2.5 w-2.5' : 'h-3 w-3',
      {
        'bg-presence-available': status === 'available',
        'bg-presence-busy': status === 'busy',
        'bg-presence-away': status === 'away',
        'bg-presence-dnd': status === 'dnd',
        'bg-presence-offline': status === 'offline',
      },
    ]"
    role="img"
    :aria-label="label"
    :title="label"
  />
</template>
