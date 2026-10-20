<script setup lang="ts">
import { Moon, Sun } from 'lucide-vue-next'
import { useActiveCall } from '@/composables/useActiveCall'
import { useTheme } from '@/composables/useTheme'
import SipStatusPill from '@/components/ui/SipStatusPill.vue'

defineProps<{ title: string }>()

const { sipState } = useActiveCall()
const { theme, toggle: toggleTheme } = useTheme()
</script>

<template>
  <header class="sticky top-0 z-20 flex h-16 shrink-0 items-center gap-3 border-b border-line/60 bg-app/80 px-4 backdrop-blur md:px-6">
    <h1 class="flex-1 truncate text-lg font-semibold tracking-tight text-fg">{{ title }}</h1>
    <SipStatusPill :state="sipState" />
    <!-- Auf dem Desktop sitzt der Theme-Schalter in der Sidebar -->
    <button
      class="rounded-lg p-2 text-muted transition-colors hover:bg-raised hover:text-fg md:hidden"
      :aria-label="theme === 'dark' ? 'Hellmodus aktivieren' : 'Dunkelmodus aktivieren'"
      @click="toggleTheme"
    >
      <Sun v-if="theme === 'dark'" class="h-4 w-4" />
      <Moon v-else class="h-4 w-4" />
    </button>
  </header>
</template>
