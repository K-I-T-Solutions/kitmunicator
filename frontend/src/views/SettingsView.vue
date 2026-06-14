<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { usePresence, STATUS_LABELS, type TeamMember } from '@/composables/usePresence'

const { loadTeam } = usePresence()

const VISIBLE_KEY = 'kitmunicator:presence:visible'

const team = ref<TeamMember[]>([])
const visible = ref<Set<string>>(new Set())
const loading = ref(true)

function save() {
  localStorage.setItem(VISIBLE_KEY, JSON.stringify([...visible.value]))
}

function toggle(userId: string) {
  if (visible.value.has(userId)) {
    visible.value.delete(userId)
  } else {
    visible.value.add(userId)
  }
  // Reaktivität erzwingen
  visible.value = new Set(visible.value)
  save()
}

function selectAll() {
  visible.value = new Set(team.value.map(m => m.user_id))
  save()
}

function selectNone() {
  visible.value = new Set()
  save()
}

onMounted(async () => {
  team.value = await loadTeam()

  const raw = localStorage.getItem(VISIBLE_KEY)
  if (raw) {
    visible.value = new Set(JSON.parse(raw) as string[])
  } else {
    // Standard: alle sichtbar
    visible.value = new Set(team.value.map(m => m.user_id))
    save()
  }

  loading.value = false
})
</script>

<template>
  <div class="settings">

    <!-- Seitenüberschrift -->
    <div class="page-header">
      <h1 class="page-title">Einstellungen</h1>
      <p class="page-sub">Passe KITmunicator an deine Bedürfnisse an.</p>
    </div>

    <!-- Sektion: Team-Anzeige -->
    <section class="section">
      <div class="section-header">
        <div class="section-label">
          <h2 class="section-title">Team-Anzeige</h2>
          <p class="section-desc">Wähle, welche Mitglieder auf dem Dashboard sichtbar sind.</p>
        </div>
        <div class="bulk-actions">
          <button class="link-btn" @click="selectAll">Alle</button>
          <span class="sep">·</span>
          <button class="link-btn" @click="selectNone">Keine</button>
        </div>
      </div>

      <div class="card">
        <div v-if="loading" class="empty-state">Lade Team…</div>

        <ul v-else class="member-list">
          <li
            v-for="member in team"
            :key="member.user_id"
            class="member-row"
            @click="toggle(member.user_id)"
          >
            <input
              type="checkbox"
              :checked="visible.has(member.user_id)"
              @change.stop="toggle(member.user_id)"
            />
            <div class="member-avatar">
              {{ member.username.charAt(0).toUpperCase() }}
            </div>
            <div class="member-info">
              <span class="member-name">{{ member.username }}</span>
              <span class="member-meta">Durchwahl {{ member.extension }}</span>
            </div>
            <span class="member-badge" :class="member.status">
              {{ STATUS_LABELS[member.status] }}
            </span>
          </li>
        </ul>
      </div>
    </section>

  </div>
</template>

<style scoped>
.settings {
  max-width: 560px;
  display: flex;
  flex-direction: column;
  gap: var(--space-8);
}

/* ── Seitenheader ── */
.page-header {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}
.page-title {
  font-size: var(--text-xl);
  font-weight: 700;
  color: var(--kit-text);
  letter-spacing: -0.01em;
}
.page-sub {
  font-size: var(--text-sm);
  color: var(--kit-text-muted);
}

/* ── Sektion ── */
.section {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.section-header {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: var(--space-4);
  padding: 0 var(--space-1);
}

.section-title {
  font-size: var(--text-sm);
  font-weight: 600;
  color: var(--kit-text);
}
.section-desc {
  font-size: var(--text-xs);
  color: var(--kit-text-muted);
  margin-top: 2px;
}

.bulk-actions {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  flex-shrink: 0;
  padding-bottom: 1px;
}
.link-btn {
  font-size: var(--text-xs);
  color: var(--kit-accent);
  cursor: pointer;
  transition: opacity var(--transition);
}
.link-btn:hover { opacity: 0.7; }
.sep { color: var(--kit-border); user-select: none; }

/* ── Card ── */
.card {
  background: var(--kit-surface);
  border: 1px solid var(--kit-border);
  border-radius: var(--radius-lg);
  overflow: hidden;
}

.empty-state {
  padding: var(--space-8);
  text-align: center;
  font-size: var(--text-sm);
  color: var(--kit-text-muted);
}

/* ── Mitglieder-Liste ── */
.member-list { list-style: none; }

.member-row {
  display: flex;
  align-items: center;
  gap: var(--space-4);
  padding: var(--space-4) var(--space-5);
  cursor: pointer;
  transition: background var(--transition);
  border-bottom: 1px solid var(--kit-border);
}
.member-row:last-child { border-bottom: none; }
.member-row:hover { background: var(--kit-surface-2); }

.member-row input[type="checkbox"] {
  width: 16px;
  height: 16px;
  accent-color: var(--kit-accent);
  flex-shrink: 0;
  cursor: pointer;
}

.member-avatar {
  width: 36px;
  height: 36px;
  border-radius: var(--radius-full);
  background: var(--kit-accent-muted);
  color: var(--kit-accent);
  font-size: var(--text-sm);
  font-weight: 600;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  user-select: none;
}

.member-info { flex: 1; min-width: 0; }
.member-name {
  display: block;
  font-size: var(--text-sm);
  font-weight: 500;
  color: var(--kit-text);
}
.member-meta {
  font-size: var(--text-xs);
  color: var(--kit-text-muted);
}

/* Status-Badge */
.member-badge {
  font-size: var(--text-xs);
  font-weight: 500;
  padding: 2px var(--space-2);
  border-radius: var(--radius-full);
  flex-shrink: 0;
}
.member-badge.available { background: rgba(34,197,94,.15);  color: #4ade80; }
.member-badge.busy      { background: rgba(239,68,68,.15);  color: #f87171; }
.member-badge.away      { background: rgba(245,158,11,.15); color: #fbbf24; }
.member-badge.dnd       { background: rgba(107,114,128,.15);color: #9ca3af; }
</style>
