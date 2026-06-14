<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { usePhone } from '@/composables/usePhone'
import { usePresence, STATUS_LABELS, type PresenceStatus, type TeamMember } from '@/composables/usePresence'

const auth = useAuthStore()
const { call } = usePhone()
const { statuses, init, subscribe, setMyStatus, loadTeam } = usePresence()

const team = ref<TeamMember[]>([])
const showStatusMenu = ref(false)

const VISIBLE_KEY = 'kitmunicator:presence:visible'

function loadVisibleIds(): Set<string> | null {
  try {
    const raw = localStorage.getItem(VISIBLE_KEY)
    return raw ? new Set(JSON.parse(raw) as string[]) : null
  } catch {
    return null
  }
}

const visibleIds = ref<Set<string> | null>(loadVisibleIds())

const visibleTeam = computed(() => {
  if (!visibleIds.value) return team.value
  return team.value.filter(m => visibleIds.value!.has(m.user_id))
})

const myStatus = computed<PresenceStatus>(() =>
  auth.userId ? (statuses[auth.userId] ?? 'available') : 'available'
)

const statusOrder: PresenceStatus[] = ['available', 'busy', 'dnd', 'away']

async function selectStatus(s: PresenceStatus) {
  showStatusMenu.value = false
  await setMyStatus(s)
}

onMounted(async () => {
  init()
  team.value = await loadTeam()
  subscribe(team.value.map(m => m.user_id))
})
</script>

<template>
  <div class="home">

    <!-- Eigener Status -->
    <section class="own-status-card">
      <div class="own-status-inner">
        <div class="own-avatar">
          <span class="dot" :class="myStatus" />
        </div>
        <div class="own-info">
          <p class="own-name">{{ auth.displayName }}</p>
          <p class="own-sub">Mein Status</p>
        </div>
        <div class="status-picker">
          <button class="status-btn" @click="showStatusMenu = !showStatusMenu">
            {{ STATUS_LABELS[myStatus] }}
            <span class="chevron">▾</span>
          </button>
          <div v-if="showStatusMenu" class="status-dropdown">
            <button
              v-for="s in statusOrder"
              :key="s"
              class="status-option"
              :class="{ active: myStatus === s }"
              @click="selectStatus(s)"
            >
              <span class="dot" :class="s" />
              {{ STATUS_LABELS[s] }}
            </button>
          </div>
        </div>
      </div>
    </section>

    <!-- Team-Übersicht -->
    <section class="team-section">
      <h2 class="section-title">Team</h2>

      <div v-if="visibleTeam.length === 0" class="empty">
        Keine Mitglieder konfiguriert — gehe zu den Einstellungen.
      </div>

      <ul v-else class="team-list">
        <li
          v-for="member in visibleTeam"
          :key="member.user_id"
          class="team-row"
        >
          <span class="dot" :class="statuses[member.user_id] ?? 'away'" />
          <div class="member-info">
            <span class="member-name">{{ member.username }}</span>
            <span class="member-ext">{{ member.extension }}</span>
          </div>
          <span class="member-status-label">
            {{ STATUS_LABELS[statuses[member.user_id] ?? 'away'] }}
          </span>
          <button
            class="call-btn"
            :disabled="statuses[member.user_id] === 'dnd' || member.user_id === auth.userId"
            :title="member.user_id === auth.userId ? 'Das bist du' : `Durchwahl ${member.extension} anrufen`"
            @click="call(member.extension)"
          >
            ☎
          </button>
        </li>
      </ul>
    </section>

  </div>
</template>

<style scoped>
.home {
  display: flex;
  flex-direction: column;
  gap: var(--space-6);
  max-width: 640px;
}

/* ── Eigener Status ── */
.own-status-card {
  background: var(--kit-surface);
  border: 1px solid var(--kit-border);
  border-radius: var(--radius);
  padding: var(--space-4) var(--space-5);
}
.own-status-inner {
  display: flex;
  align-items: center;
  gap: var(--space-4);
}
.own-avatar {
  width: 40px;
  height: 40px;
  border-radius: var(--radius-full);
  background: var(--kit-surface-2);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.own-info { flex: 1; }
.own-name { font-weight: 600; font-size: var(--text-sm); color: var(--kit-text); }
.own-sub  { font-size: var(--text-xs); color: var(--kit-text-muted); }

.status-picker { position: relative; }
.status-btn {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-3);
  background: var(--kit-surface-2);
  border: 1px solid var(--kit-border);
  border-radius: var(--radius);
  font-size: var(--text-sm);
  color: var(--kit-text);
  cursor: pointer;
  transition: background var(--transition);
}
.status-btn:hover { background: var(--kit-surface-3, var(--kit-surface)); }
.chevron { font-size: 10px; color: var(--kit-text-muted); }

.status-dropdown {
  position: absolute;
  top: calc(100% + 6px);
  right: 0;
  background: var(--kit-surface);
  border: 1px solid var(--kit-border);
  border-radius: var(--radius);
  box-shadow: var(--shadow);
  padding: var(--space-1);
  min-width: 180px;
  z-index: 50;
}
.status-option {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  width: 100%;
  padding: var(--space-2) var(--space-3);
  border-radius: var(--radius-sm);
  font-size: var(--text-sm);
  color: var(--kit-text-muted);
  text-align: left;
  transition: background var(--transition), color var(--transition);
}
.status-option:hover { background: var(--kit-surface-2); color: var(--kit-text); }
.status-option.active { color: var(--kit-text); font-weight: 500; }

/* ── Team ── */
.section-title {
  font-size: var(--text-xs);
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--kit-text-muted);
  margin-bottom: var(--space-3);
}

.team-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  list-style: none;
}

.team-row {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-3) var(--space-4);
  border-radius: var(--radius);
  background: var(--kit-surface);
  border: 1px solid var(--kit-border);
  transition: background var(--transition);
}
.team-row:hover { background: var(--kit-surface-2); }

.member-info {
  flex: 1;
  display: flex;
  align-items: baseline;
  gap: var(--space-2);
}
.member-name { font-size: var(--text-sm); font-weight: 500; color: var(--kit-text); }
.member-ext  { font-size: var(--text-xs); color: var(--kit-text-muted); font-variant-numeric: tabular-nums; }

.member-status-label {
  font-size: var(--text-xs);
  color: var(--kit-text-muted);
  min-width: 90px;
  text-align: right;
}

.call-btn {
  width: 32px;
  height: 32px;
  border-radius: var(--radius-full);
  background: var(--kit-accent-muted);
  color: var(--kit-accent);
  font-size: var(--text-sm);
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background var(--transition), opacity var(--transition);
  flex-shrink: 0;
}
.call-btn:hover:not(:disabled) { background: var(--kit-accent); color: #fff; }
.call-btn:disabled { opacity: 0.35; cursor: not-allowed; }

/* ── Dots (gleiche Farben wie PresenceBadge) ── */
.dot {
  width: 10px;
  height: 10px;
  border-radius: var(--radius-full);
  flex-shrink: 0;
}
.dot.available { background: var(--presence-available); }
.dot.busy      { background: var(--presence-busy); }
.dot.away      { background: var(--presence-away); }
.dot.dnd       { background: var(--presence-dnd); }

.empty {
  font-size: var(--text-sm);
  color: var(--kit-text-muted);
  padding: var(--space-4);
  text-align: center;
  border: 1px dashed var(--kit-border);
  border-radius: var(--radius);
}
</style>
