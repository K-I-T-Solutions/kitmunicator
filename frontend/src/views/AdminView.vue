<script setup lang="ts">
import { ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Activity, UsersRound, UserCog } from 'lucide-vue-next'
import AdminUsers from '@/components/admin/AdminUsers.vue'
import AdminStatus from '@/components/admin/AdminStatus.vue'
import AdminGroups from '@/components/admin/AdminGroups.vue'

const TABS = [
  { id: 'users', label: 'Benutzer', icon: UserCog },
  { id: 'groups', label: 'Gruppen', icon: UsersRound },
  { id: 'status', label: 'Status', icon: Activity },
] as const
type TabId = (typeof TABS)[number]['id']

const route = useRoute()
const router = useRouter()

// Tab in der URL (?tab=status), damit Neuladen und Links funktionieren
const tab = ref<TabId>(TABS.some(t => t.id === route.query.tab) ? (route.query.tab as TabId) : 'users')
watch(tab, t => router.replace({ query: t === 'users' ? {} : { tab: t } }))
</script>

<template>
  <div class="mx-auto max-w-5xl px-4 py-6 md:px-6">
    <div class="mb-5 flex gap-1 overflow-x-auto rounded-xl bg-raised p-1" role="tablist" aria-label="Verwaltung">
      <button
        v-for="t in TABS"
        :key="t.id"
        role="tab"
        :aria-selected="tab === t.id"
        class="flex shrink-0 items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition-colors"
        :class="tab === t.id ? 'bg-surface text-fg shadow-sm' : 'text-muted hover:text-fg'"
        @click="tab = t.id"
      >
        <component :is="t.icon" class="h-4 w-4" /> {{ t.label }}
      </button>
    </div>

    <AdminUsers v-if="tab === 'users'" />
    <AdminGroups v-else-if="tab === 'groups'" />
    <AdminStatus v-else />
  </div>
</template>
