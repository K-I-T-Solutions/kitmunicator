<script setup lang="ts">
import { onMounted } from 'vue'
import { RouterView, RouterLink, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { usePhoneStore } from '@/stores/phone'
import { usePhone } from '@/composables/usePhone'
import PresenceBadge from '@/components/shared/PresenceBadge.vue'
import IncomingCallOverlay from '@/components/shared/IncomingCallOverlay.vue'
import { usePresence } from '@/composables/usePresence'

const auth = useAuthStore()
const phone = usePhoneStore()
const { register } = usePhone()
const { init: initPresence } = usePresence()
const route = useRoute()

onMounted(async () => {
  if (auth.isAuthenticated) {
    await register()
    initPresence()
  }
})

const navItems = [
  { to: '/',         label: 'Team',          icon: '👥' },
  { to: '/dialer',   label: 'Dialer',        icon: '☎' },
  { to: '/contacts', label: 'Kontakte',      icon: '📋' },
  { to: '/settings', label: 'Einstellungen', icon: '⚙' },
]
</script>

<template>
  <div class="layout">
    <!-- Sidebar -->
    <aside class="sidebar">
      <div class="sidebar-logo">
        <img src="/kitmunicator_icon.png" height="32" width="32" alt="" />
        <span class="brand-kit">KIT</span><span class="brand-munic">municator</span>
      </div>

      <nav class="sidebar-nav">
        <RouterLink
          v-for="item in navItems"
          :key="item.to"
          :to="item.to"
          class="nav-item"
          :class="{ active: item.to === '/' ? route.path === '/' : route.path.startsWith(item.to) }"
        >
          <span class="nav-icon">{{ item.icon }}</span>
          <span>{{ item.label }}</span>
        </RouterLink>
      </nav>

      <div class="sidebar-footer">
        <PresenceBadge
          v-if="auth.userId"
          :user-id="auth.userId"
          :editable="true"
        />
        <span class="user-name">{{ auth.displayName }}</span>
        <button class="btn-logout" @click="auth.logout()">Abmelden</button>
      </div>
    </aside>

    <!-- Hauptbereich -->
    <div class="main">
      <header class="topbar">
        <div class="topbar-title">{{ route.meta?.title ?? '' }}</div>
        <div class="topbar-status">
          <span
            class="sip-indicator"
            :class="phone.callState"
            :title="`SIP: ${phone.callState}`"
          />
          <span class="sip-label">{{ phone.callState }}</span>
        </div>
      </header>

      <main class="content">
        <RouterView />
      </main>
    </div>

    <!-- Eingehender Anruf – global, immer sichtbar -->
    <IncomingCallOverlay />
  </div>
</template>

<style scoped>
.layout {
  display: flex;
  height: 100vh;
  overflow: hidden;
}

/* ── Sidebar ── */
.sidebar {
  width: var(--sidebar-width);
  background: var(--kit-surface);
  border-right: 1px solid var(--kit-border);
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
}

.sidebar-logo {
  padding: var(--space-4);
  font-size: var(--text-xl);
  letter-spacing: -0.02em;
  line-height: 1;
  white-space: nowrap;
  display: flex;
  align-items: center;
  gap: var(--space-2);
}
.sidebar-logo img { flex-shrink: 0; }

.sidebar-nav {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  padding: 0 var(--space-2);
}

.nav-item {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-2) var(--space-3);
  border-radius: var(--radius);
  color: var(--kit-text-muted);
  font-size: var(--text-sm);
  font-weight: 500;
  transition: background var(--transition), color var(--transition);
  text-decoration: none;
}
.nav-item:hover { background: var(--kit-surface-2); color: var(--kit-text); }
.nav-item.active { background: var(--kit-accent-muted); color: var(--kit-accent); }
.nav-icon { width: 1.25rem; text-align: center; }

.sidebar-footer {
  padding: var(--space-4);
  border-top: 1px solid var(--kit-border);
  display: flex;
  align-items: center;
  gap: var(--space-2);
  flex-wrap: wrap;
}
.user-name {
  flex: 1;
  font-size: var(--text-sm);
  color: var(--kit-text-muted);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.btn-logout {
  font-size: var(--text-xs);
  color: var(--kit-text-muted);
  padding: var(--space-1) var(--space-2);
  border-radius: var(--radius-sm);
  transition: color var(--transition);
}
.btn-logout:hover { color: var(--kit-danger); }

/* ── Hauptbereich ── */
.main {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.topbar {
  height: var(--topbar-height);
  background: var(--kit-surface);
  border-bottom: 1px solid var(--kit-border);
  display: flex;
  align-items: center;
  padding: 0 var(--space-6);
  gap: var(--space-4);
  flex-shrink: 0;
}
.topbar-title { font-weight: 600; flex: 1; }
.topbar-status {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-size: var(--text-xs);
  color: var(--kit-text-muted);
}

.sip-indicator {
  width: 8px; height: 8px;
  border-radius: var(--radius-full);
  background: var(--kit-text-muted);
}
.sip-indicator.registered  { background: var(--kit-success); }
.sip-indicator.calling,
.sip-indicator.incoming,
.sip-indicator.connected   { background: var(--kit-warning); }
.sip-indicator.error       { background: var(--kit-danger); }

.content {
  flex: 1;
  overflow-y: auto;
  padding: var(--space-6);
}
</style>
