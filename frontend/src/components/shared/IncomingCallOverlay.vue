<script setup lang="ts">
import { computed } from 'vue'
import { usePhone } from '@/composables/usePhone'

const { callState, remoteNumber, answer, hangup } = usePhone()
const visible = computed(() => callState.value === 'incoming')
</script>

<template>
  <Transition name="slide-up">
    <div v-if="visible" class="overlay" role="alertdialog" aria-label="Eingehender Anruf">
      <div class="overlay-card">
        <div class="caller-avatar">
          {{ (remoteNumber ?? '?')[0]?.toUpperCase() }}
        </div>

        <div class="caller-info">
          <span class="caller-label">Eingehender Anruf</span>
          <span class="caller-number">{{ remoteNumber }}</span>
        </div>

        <div class="actions">
          <button class="btn-reject" @click="hangup()" aria-label="Ablehnen">
            ✕
          </button>
          <button class="btn-accept" @click="answer()" aria-label="Annehmen">
            ☎
          </button>
        </div>
      </div>
    </div>
  </Transition>
</template>

<style scoped>
.overlay {
  position: fixed;
  bottom: var(--space-6);
  right: var(--space-6);
  z-index: 9999;
}

.overlay-card {
  display: flex;
  align-items: center;
  gap: var(--space-4);
  background: var(--kit-surface);
  border: 1px solid var(--kit-border);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-lg);
  padding: var(--space-4) var(--space-6);
  min-width: 320px;
  animation: pulse-border 1.5s ease infinite;
}

@keyframes pulse-border {
  0%, 100% { border-color: var(--kit-border); }
  50%       { border-color: var(--kit-accent); }
}

.caller-avatar {
  width: 48px;
  height: 48px;
  border-radius: var(--radius-full);
  background: var(--kit-accent-muted);
  color: var(--kit-accent);
  font-size: var(--text-xl);
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.caller-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}
.caller-label {
  font-size: var(--text-xs);
  color: var(--kit-text-muted);
}
.caller-number {
  font-size: var(--text-lg);
  font-weight: 600;
}

.actions {
  display: flex;
  gap: var(--space-3);
}

.btn-reject,
.btn-accept {
  width: 44px;
  height: 44px;
  border-radius: var(--radius-full);
  font-size: var(--text-lg);
  display: flex;
  align-items: center;
  justify-content: center;
  transition: transform var(--transition), background var(--transition);
}
.btn-reject:hover, .btn-accept:hover { transform: scale(1.1); }

.btn-reject {
  background: var(--kit-danger);
  color: white;
}
.btn-reject:hover { background: var(--kit-danger-hover); }

.btn-accept {
  background: var(--kit-success);
  color: white;
}
.btn-accept:hover { filter: brightness(1.15); }

/* Transition */
.slide-up-enter-active,
.slide-up-leave-active {
  transition: transform 250ms ease, opacity 250ms ease;
}
.slide-up-enter-from,
.slide-up-leave-to {
  transform: translateY(16px);
  opacity: 0;
}
</style>
