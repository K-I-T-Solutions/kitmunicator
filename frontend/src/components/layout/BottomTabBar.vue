<script setup lang="ts">
import { RouterLink, useRoute } from 'vue-router'
import { NAV_ITEMS, isActive } from './navigation'

const route = useRoute()
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
      <component :is="item.icon" class="h-5 w-5" />
      <span class="text-[10px] font-medium">{{ item.label }}</span>
    </RouterLink>
  </nav>
</template>
