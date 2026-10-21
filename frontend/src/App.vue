<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { RouterView, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { usePhone } from '@/composables/usePhone'
import { usePresence } from '@/composables/usePresence'
import { useActiveCall } from '@/composables/useActiveCall'
import { useVoicemail } from '@/composables/useVoicemail'
import AppSidebar from '@/components/layout/AppSidebar.vue'
import AppTopBar from '@/components/layout/AppTopBar.vue'
import BottomTabBar from '@/components/layout/BottomTabBar.vue'
import ActiveCallBar from '@/components/call/ActiveCallBar.vue'
import IncomingCallModal from '@/components/call/IncomingCallModal.vue'
import CallErrorToast from '@/components/call/CallErrorToast.vue'
import MissedCallToasts from '@/components/call/MissedCallToasts.vue'
import { useCallNotifications } from '@/composables/useCallNotifications'

const auth = useAuthStore()
const { callState, register } = usePhone()
const { init: initPresence, loadTeam, subscribe } = usePresence()
const { hasActiveCall } = useActiveCall()
const { startPolling: pollVoicemail } = useVoicemail()
const { start: startCallNotifications } = useCallNotifications()
const route = useRoute()

onMounted(async () => {
  if (!auth.isAuthenticated) return
  initPresence()
  // Team früh laden: Sidebar (eigene Durchwahl) und Anrufer-Namen brauchen es
  loadTeam().then(members => subscribe(members.map(m => m.user_id)))
  pollVoicemail()
  startCallNotifications()
  await register()
})

const title = computed(() => (route.meta?.title as string | undefined) ?? '')

// Auf der Telefon-Seite zeigt das Wählfeld den Anruf selbst
const showCallBar = computed(() => hasActiveCall.value && route.name !== 'dialer')
</script>

<template>
  <div class="flex h-full overflow-hidden">
    <AppSidebar />

    <div class="flex min-w-0 flex-1 flex-col">
      <AppTopBar :title="title" />
      <main
        class="scrollbar-thin flex-1 overflow-y-auto"
        :class="showCallBar ? 'pb-40 md:pb-28' : 'pb-20 md:pb-0'"
      >
        <RouterView />
      </main>
    </div>

    <BottomTabBar />
    <ActiveCallBar v-if="showCallBar" />
    <IncomingCallModal v-if="callState === 'incoming'" />
    <CallErrorToast />
    <MissedCallToasts />
  </div>
</template>
