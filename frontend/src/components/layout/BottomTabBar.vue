<script setup lang="ts">
import { RouterLink, useRoute } from 'vue-router'
import { useVoicemail } from '@/composables/useVoicemail'
import { NAV_ITEMS, isActive } from './navigation'

const route = useRoute()
const { unreadCount } = useVoicemail()
</script>

<template>
  <nav
    class="fixed inset-x-0 bottom-0 z-30 grid border-t border-line/60 bg-surface/95 pb-[env(safe-area-inset-bottom)] backdrop-blur md:hidden"
    :style="{ gridTemplateColumns: `repeat(${NAV_ITEMS.length}, minmax(0, 1fr))` }"
    aria-label="Hauptnavigation"
  >
    <RouterLink
      v-for="item in NAV_ITEMS"
      :key="item.to"
      :to="item.to"
      class="flex flex-col items-center justify-center gap-1 py-2.5 transition-colors"
      :class="isActive(item, route.path) ? 'text-brand' : 'text-muted'"
      :aria-current="isActive(item, route.path) ? 'page' : undefined"
    >
      <span class="relative">
        <component :is="item.icon" class="h-5 w-5" />
        <span
          v-if="item.badge === 'voicemail' && unreadCount"
          class="tabular absolute -right-2.5 -top-1.5 min-w-[1rem] rounded-full bg-accent-500 px-1 py-0.5 text-center text-[9px] font-semibold leading-none text-white"
          :aria-label="`${unreadCount} neu`"
        >{{ unreadCount }}</span>
      </span>
      <span class="text-[10px] font-medium">{{ item.label }}</span>
    </RouterLink>
  </nav>
</template>
