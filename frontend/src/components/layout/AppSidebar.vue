<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import { LogOut, Moon, Sun } from 'lucide-vue-next'
import { useAuthStore } from '@/stores/auth'
import { usePresence, STATUS_LABELS } from '@/composables/usePresence'
import { useTheme } from '@/composables/useTheme'
import { useVoicemail } from '@/composables/useVoicemail'
import AppLogo from '@/components/ui/AppLogo.vue'
import UserAvatar from '@/components/ui/UserAvatar.vue'
import PresenceDot from '@/components/ui/PresenceDot.vue'
import { NAV_ITEMS, isActive } from './navigation'

const route = useRoute()
const auth = useAuthStore()
const { statuses, team } = usePresence()
const { theme, toggle: toggleTheme } = useTheme()
const { unreadCount } = useVoicemail()

const myStatus = computed(() => (auth.userId && statuses[auth.userId]) || 'available')
const myExtension = computed(() => team.value.find(m => m.user_id === auth.userId)?.extension)
</script>

<template>
  <aside class="hidden w-64 shrink-0 flex-col border-r border-line/60 bg-surface/60 md:flex">
    <div class="flex h-16 items-center justify-between border-b border-line/60 px-5">
      <AppLogo />
      <button
        class="rounded-lg p-1.5 text-muted transition-colors hover:bg-raised hover:text-fg"
        :aria-label="theme === 'dark' ? 'Hellmodus aktivieren' : 'Dunkelmodus aktivieren'"
        :title="theme === 'dark' ? 'Hellmodus' : 'Dunkelmodus'"
        @click="toggleTheme"
      >
        <Sun v-if="theme === 'dark'" class="h-4 w-4" />
        <Moon v-else class="h-4 w-4" />
      </button>
    </div>

    <nav class="flex-1 space-y-1 px-3 py-4" aria-label="Hauptnavigation">
      <RouterLink
        v-for="item in NAV_ITEMS"
        :key="item.to"
        :to="item.to"
        class="flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-colors"
        :class="isActive(item, route.path)
          ? 'bg-cyan-500/10 text-brand ring-1 ring-cyan-500/20'
          : 'text-muted hover:bg-raised hover:text-fg'"
        :aria-current="isActive(item, route.path) ? 'page' : undefined"
      >
        <component :is="item.icon" class="h-5 w-5 shrink-0" />
        <span class="flex-1">{{ item.label }}</span>
        <span
          v-if="item.badge === 'voicemail' && unreadCount"
          class="tabular min-w-[1.25rem] rounded-full bg-accent-500 px-1.5 py-0.5 text-center text-[11px] font-semibold leading-none text-white"
          :aria-label="`${unreadCount} neu`"
        >{{ unreadCount }}</span>
      </RouterLink>
    </nav>

    <div class="m-3 mt-0 flex items-center gap-3 rounded-xl border border-line/60 p-3">
      <div class="relative">
        <UserAvatar :name="auth.displayName || '?'" />
        <PresenceDot :status="myStatus" size="xs" class="absolute -bottom-0.5 -right-0.5" />
      </div>
      <div class="min-w-0 flex-1">
        <p class="truncate text-sm font-medium text-fg">{{ auth.displayName }}</p>
        <p class="truncate text-xs text-muted">
          <template v-if="myExtension">Nebenstelle {{ myExtension }} · </template>{{ STATUS_LABELS[myStatus] }}
        </p>
      </div>
      <button
        class="rounded-lg p-1.5 text-subtle transition-colors hover:bg-red-500/10 hover:text-red-500"
        aria-label="Abmelden"
        title="Abmelden"
        @click="auth.logout()"
      >
        <LogOut class="h-4 w-4" />
      </button>
    </div>
  </aside>
</template>
