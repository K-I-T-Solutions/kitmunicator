<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { Phone, Search, Users } from 'lucide-vue-next'
import { useAuthStore } from '@/stores/auth'
import { usePhone } from '@/composables/usePhone'
import { usePresence, STATUS_LABELS, type PresenceStatus, type TeamMember } from '@/composables/usePresence'
import { useTeamVisibility } from '@/composables/useTeamVisibility'
import UserAvatar from '@/components/ui/UserAvatar.vue'
import PresenceDot from '@/components/ui/PresenceDot.vue'
import PresencePicker from '@/components/ui/PresencePicker.vue'
import PhoneStateBadge from '@/components/ui/PhoneStateBadge.vue'

const auth = useAuthStore()
const { call, isBusy } = usePhone()
const { statuses, phoneStatuses, team, subscribe, setMyStatus, loadTeam } = usePresence()
const { isVisible } = useTeamVisibility()

const loading = ref(team.value.length === 0)
const query = ref('')

const me = computed(() => team.value.find(m => m.user_id === auth.userId))
const myStatus = computed<PresenceStatus>(() => (auth.userId && statuses[auth.userId]) || 'available')

const colleagues = computed(() => team.value.filter(m => m.user_id !== auth.userId))
const shown = computed(() => colleagues.value.filter(m => isVisible(m.user_id)))
const filtered = computed(() => {
  const q = query.value.trim().toLowerCase()
  if (!q) return shown.value
  return shown.value.filter(m => m.username.toLowerCase().includes(q) || m.extension.includes(q))
})

function statusOf(member: TeamMember): PresenceStatus {
  return statuses[member.user_id] ?? member.status
}
function phoneOf(member: TeamMember) {
  return phoneStatuses[member.user_id] ?? member.phone_status
}
function canCall(member: TeamMember): boolean {
  return !isBusy.value && statusOf(member) !== 'dnd'
}
function callTitle(member: TeamMember): string {
  if (isBusy.value) return 'Du bist bereits in einem Gespräch'
  if (statusOf(member) === 'dnd') return `${member.username} möchte nicht gestört werden`
  return `Durchwahl ${member.extension} anrufen`
}

onMounted(async () => {
  const members = await loadTeam()
  subscribe(members.map(m => m.user_id))
  loading.value = false
})
</script>

<template>
  <div class="mx-auto max-w-5xl space-y-6 px-4 py-6 md:px-6">
    <!-- Mein Status -->
    <section class="rounded-2xl border border-line/60 bg-surface p-5" aria-labelledby="my-status-title">
      <h2 id="my-status-title" class="mb-4 flex items-center gap-2 text-xs font-medium uppercase tracking-wider text-muted">
        <Users class="h-3.5 w-3.5" /> Mein Status
      </h2>
      <div class="flex flex-wrap items-center gap-4">
        <div class="relative">
          <UserAvatar :name="auth.displayName || '?'" size="lg" />
          <PresenceDot :status="myStatus" class="absolute -bottom-0.5 -right-0.5" />
        </div>
        <!-- Mindestbreite: auf schmalen Displays rutscht der Status-Auswähler in eine eigene Zeile -->
        <div class="min-w-[11rem] flex-1">
          <p class="truncate text-lg font-semibold text-fg">{{ auth.displayName }}</p>
          <p class="text-sm text-muted">
            <template v-if="me">Nebenstelle {{ me.extension }}</template>
            <template v-else-if="!loading">Kein SIP-Account eingerichtet</template>
          </p>
        </div>
        <PresencePicker :model-value="myStatus" @update:model-value="setMyStatus" />
      </div>
    </section>

    <!-- Team -->
    <section aria-labelledby="team-title">
      <div class="mb-4 flex items-center justify-between gap-3">
        <h2 id="team-title" class="text-sm font-semibold text-fg">Teammitglieder</h2>
        <label class="relative max-w-xs flex-1">
          <span class="sr-only">Team durchsuchen</span>
          <Search class="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-subtle" />
          <input
            v-model="query"
            type="search"
            placeholder="Name oder Durchwahl…"
            class="w-full rounded-lg border border-line/60 bg-surface py-2 pl-9 pr-3 text-sm text-fg placeholder:text-subtle focus:border-cyan-500/50 focus:outline-none focus:ring-1 focus:ring-cyan-500/50"
          />
        </label>
      </div>

      <!-- Laden -->
      <div v-if="loading" class="grid gap-3 sm:grid-cols-2" aria-busy="true">
        <div v-for="i in 4" :key="i" class="flex animate-pulse items-center gap-3 rounded-xl border border-line/60 bg-surface p-3.5">
          <span class="h-10 w-10 rounded-full bg-raised" />
          <div class="flex-1 space-y-2">
            <span class="block h-3 w-1/3 rounded bg-raised" />
            <span class="block h-2.5 w-1/4 rounded bg-raised" />
          </div>
        </div>
      </div>

      <!-- Leer -->
      <div v-else-if="filtered.length === 0" class="flex flex-col items-center justify-center rounded-2xl border border-dashed border-line py-14 text-center">
        <span class="mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-raised text-subtle">
          <Users class="h-6 w-6" />
        </span>
        <template v-if="colleagues.length === 0">
          <p class="text-sm text-fg">Noch keine Kollegen mit SIP-Account.</p>
        </template>
        <template v-else-if="shown.length === 0">
          <p class="text-sm text-fg">Keine Mitglieder ausgewählt.</p>
          <RouterLink to="/settings" class="mt-1 text-sm text-brand hover:underline">In den Einstellungen auswählen</RouterLink>
        </template>
        <template v-else>
          <p class="text-sm text-fg">Niemand gefunden für „{{ query }}“.</p>
        </template>
      </div>

      <!-- Liste -->
      <ul v-else class="grid gap-3 sm:grid-cols-2">
        <li
          v-for="member in filtered"
          :key="member.user_id"
          class="group flex items-center gap-3 rounded-xl border border-line/60 bg-surface p-3.5 transition-colors hover:border-line"
        >
          <div class="relative" :class="{ 'opacity-60': phoneOf(member) === 'offline' }">
            <UserAvatar :name="member.username" />
            <PresenceDot :status="statusOf(member)" size="xs" class="absolute -bottom-0.5 -right-0.5" />
          </div>
          <div class="min-w-0 flex-1">
            <div class="flex items-baseline gap-2">
              <p class="truncate text-sm font-medium text-fg">{{ member.username }}</p>
              <span class="font-mono text-xs text-subtle">{{ member.extension }}</span>
            </div>
            <div class="mt-0.5 flex flex-wrap items-center gap-x-2">
              <PhoneStateBadge v-if="phoneOf(member) === 'ringing' || phoneOf(member) === 'in_call'" :state="phoneOf(member)" />
              <template v-else>
                <span class="text-xs text-muted">{{ STATUS_LABELS[statusOf(member)] }}</span>
                <template v-if="phoneOf(member) === 'offline'">
                  <span class="text-xs text-subtle" aria-hidden="true">·</span>
                  <PhoneStateBadge state="offline" />
                </template>
              </template>
            </div>
          </div>
          <button
            class="flex shrink-0 items-center gap-1.5 rounded-lg bg-cyan-500/10 px-2.5 py-1.5 text-xs font-medium text-brand transition-colors hover:bg-cyan-500/20 disabled:cursor-not-allowed disabled:opacity-40"
            :disabled="!canCall(member)"
            :title="callTitle(member)"
            :aria-label="`${member.username} anrufen`"
            @click="call(member.extension, member.username)"
          >
            <Phone class="h-3.5 w-3.5" />
            <span class="hidden sm:inline">Anrufen</span>
          </button>
        </li>
      </ul>
    </section>
  </div>
</template>
