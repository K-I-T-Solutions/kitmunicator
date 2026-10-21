<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { CircleAlert, KeyRound, Lock, LockOpen, Pencil, Plus, Search, Trash2, TriangleAlert } from 'lucide-vue-next'
import { useAdmin, type AdminUser } from '@/composables/useAdmin'
import UserAvatar from '@/components/ui/UserAvatar.vue'

const admin = useAdmin()
const { users, keycloakError, nextExtension, loadState } = admin

const search = ref('')
const filter = ref<'all' | 'with' | 'without'>('all')
const notice = ref<{ kind: 'ok' | 'error'; text: string } | null>(null)

const filtered = computed(() => {
  const q = search.value.trim().toLowerCase()
  return users.value.filter((u) => {
    if (filter.value === 'with' && !u.sip) return false
    if (filter.value === 'without' && u.sip) return false
    if (!q) return true
    return [u.display_name, u.username, u.email ?? '', u.sip?.extension ?? ''].some(v => v.toLowerCase().includes(q))
  })
})
const filterTabs = computed(() => [
  { id: 'all' as const, label: 'Alle', count: users.value.length },
  { id: 'with' as const, label: 'Mit Nebenstelle', count: users.value.filter(u => u.sip).length },
  { id: 'without' as const, label: 'Ohne', count: users.value.filter(u => !u.sip).length },
])

// ── Bearbeiten / Zuweisen (eine Zeile gleichzeitig) ─────────────────────────
const editing = ref<string | null>(null)
const form = reactive({ extension: '', display_name: '' })
const busy = ref(false)
/** Zweiter Klick bestätigt – "<user_id>:<aktion>" */
const confirming = ref<string | null>(null)

function openEditor(user: AdminUser) {
  editing.value = user.user_id
  confirming.value = null
  form.extension = user.sip?.extension ?? nextExtension.value ?? ''
  form.display_name = user.sip?.display_name ?? user.display_name
}

async function run(action: () => Promise<unknown>, success: string) {
  busy.value = true
  notice.value = null
  try {
    await action()
    notice.value = { kind: 'ok', text: success }
    editing.value = null
    confirming.value = null
    await admin.loadUsers()
  } catch (err) {
    notice.value = { kind: 'error', text: err instanceof Error ? err.message : String(err) }
  } finally {
    busy.value = false
  }
}

function save(user: AdminUser) {
  if (user.sip) {
    const sip = user.sip
    run(() => admin.updateSip(sip.id, { extension: form.extension, display_name: form.display_name }),
      `${form.display_name || user.display_name} gespeichert.`)
  } else {
    run(() => admin.assignSip(user.user_id, form.extension, form.display_name),
      `${form.display_name || user.display_name} hat jetzt die Durchwahl ${form.extension}.`)
  }
}

function confirmOr(user: AdminUser, action: string, run: () => void) {
  const key = `${user.user_id}:${action}`
  if (confirming.value === key) run()
  else confirming.value = key
}

function toggleActive(user: AdminUser) {
  const sip = user.sip!
  run(() => admin.updateSip(sip.id, { is_active: !sip.is_active }),
    sip.is_active ? `${user.display_name} gesperrt – kann nicht mehr telefonieren.` : `${user.display_name} freigegeben.`)
}

function resetPassword(user: AdminUser) {
  confirmOr(user, 'password', () => run(() => admin.resetPassword(user.sip!.id),
    `Neues SIP-Passwort für ${user.display_name}. Die App übernimmt es beim nächsten Neuladen.`))
}

function remove(user: AdminUser) {
  confirmOr(user, 'delete', () => run(() => admin.deleteSip(user.sip!.id),
    `Nebenstelle ${user.sip!.extension} von ${user.display_name} entfernt.`))
}

function statusOf(user: AdminUser): { label: string; cls: string } {
  if (!user.sip) return { label: 'Keine Nebenstelle', cls: 'text-subtle' }
  if (!user.sip.is_active) return { label: 'Gesperrt', cls: 'text-red-600 dark:text-red-400' }
  if (user.sip.online) return { label: 'Online', cls: 'text-emerald-600 dark:text-emerald-400' }
  return { label: 'Offline', cls: 'text-subtle' }
}

onMounted(admin.loadUsers)
</script>

<template>
  <section class="rounded-2xl border border-line/60 bg-surface">
    <div class="flex flex-wrap items-center gap-3 border-b border-line/60 p-4">
      <label class="relative min-w-[12rem] flex-1">
        <Search class="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-subtle" />
        <span class="sr-only">Suchen</span>
        <input
          v-model="search"
          type="search"
          placeholder="Name, E-Mail oder Durchwahl"
          class="w-full rounded-lg border border-line bg-app py-2 pl-9 pr-3 text-sm text-fg placeholder:text-subtle focus:border-cyan-500 focus:outline-none"
        />
      </label>
      <div class="flex gap-1 rounded-lg bg-raised p-1 text-xs font-medium" role="tablist">
        <button
          v-for="tab in filterTabs"
          :key="tab.id"
          role="tab"
          :aria-selected="filter === tab.id"
          class="rounded-md px-2.5 py-1.5 transition-colors"
          :class="filter === tab.id ? 'bg-surface text-fg shadow-sm' : 'text-muted hover:text-fg'"
          @click="filter = tab.id"
        >{{ tab.label }} <span class="tabular text-subtle">{{ tab.count }}</span></button>
      </div>
    </div>

    <div v-if="keycloakError" class="flex items-start gap-2 border-b border-line/60 bg-amber-500/10 px-4 py-3 text-sm text-amber-700 dark:text-amber-300">
      <TriangleAlert class="mt-0.5 h-4 w-4 shrink-0" />
      <p>{{ keycloakError }} – es werden nur bestehende Nebenstellen angezeigt, Zuweisen ist nicht möglich.</p>
    </div>
    <p
      v-if="notice"
      class="border-b border-line/60 px-4 py-2.5 text-sm"
      :class="notice.kind === 'ok' ? 'text-emerald-700 dark:text-emerald-300' : 'text-red-600 dark:text-red-400'"
      role="status"
    >{{ notice.text }}</p>

    <div v-if="loadState === 'loading'" class="space-y-2 p-4" aria-busy="true">
      <div v-for="n in 4" :key="n" class="h-14 animate-pulse rounded-xl bg-raised" />
    </div>
    <div v-else-if="loadState === 'error'" class="flex flex-col items-center py-12 text-center">
      <CircleAlert class="mb-2 h-6 w-6 text-subtle" />
      <p class="text-sm text-muted">Benutzer konnten nicht geladen werden.</p>
      <button class="mt-2 text-sm text-brand hover:underline" @click="admin.loadUsers()">Erneut versuchen</button>
    </div>
    <p v-else-if="filtered.length === 0" class="py-12 text-center text-sm text-muted">Keine Treffer.</p>

    <ul v-else class="divide-y divide-line/50">
      <li v-for="user in filtered" :key="user.user_id" class="px-4 py-3">
        <div class="flex flex-wrap items-center gap-3">
          <UserAvatar :name="user.sip?.display_name || user.display_name" />
          <div class="min-w-0 flex-1">
            <p class="flex flex-wrap items-center gap-2 text-sm font-medium text-fg">
              <span class="truncate">{{ user.sip?.display_name || user.display_name }}</span>
              <span v-if="!user.in_keycloak && !keycloakError" class="whitespace-nowrap rounded bg-amber-500/15 px-1.5 py-0.5 text-[10px] font-semibold uppercase text-amber-700 dark:text-amber-300">nicht in Keycloak</span>
              <span v-if="!user.enabled" class="whitespace-nowrap rounded bg-raised px-1.5 py-0.5 text-[10px] font-semibold uppercase text-subtle">Login deaktiviert</span>
            </p>
            <p class="truncate text-xs text-subtle">{{ user.username }}<template v-if="user.email"> · {{ user.email }}</template></p>
          </div>
          <div class="shrink-0 text-right">
            <p v-if="user.sip" class="tabular font-mono text-sm text-fg">{{ user.sip.extension }}</p>
            <p class="text-xs" :class="statusOf(user).cls">{{ statusOf(user).label }}</p>
          </div>

          <!-- Mobil eigene Zeile, damit der Name Platz hat -->
          <div class="flex w-full items-center justify-end gap-1 sm:w-auto">
            <template v-if="user.sip">
              <button class="rounded-lg p-2 text-muted transition-colors hover:bg-raised hover:text-fg" title="Bearbeiten" aria-label="Bearbeiten" @click="openEditor(user)">
                <Pencil class="h-4 w-4" />
              </button>
              <button
                class="rounded-lg p-2 transition-colors hover:bg-raised"
                :class="user.sip.is_active ? 'text-muted hover:text-fg' : 'text-red-500'"
                :title="user.sip.is_active ? 'Sperren' : 'Freigeben'"
                :aria-label="user.sip.is_active ? 'Sperren' : 'Freigeben'"
                :disabled="busy"
                @click="toggleActive(user)"
              >
                <Lock v-if="user.sip.is_active" class="h-4 w-4" />
                <LockOpen v-else class="h-4 w-4" />
              </button>
              <button
                class="rounded-lg p-2 text-xs font-medium transition-colors"
                :class="confirming === `${user.user_id}:password` ? 'bg-amber-500 px-2.5 text-white' : 'text-muted hover:bg-raised hover:text-fg'"
                :title="confirming === `${user.user_id}:password` ? undefined : 'SIP-Passwort neu erzeugen'"
                :disabled="busy"
                @click="resetPassword(user)"
              >
                <span v-if="confirming === `${user.user_id}:password`">Neu erzeugen?</span>
                <KeyRound v-else class="h-4 w-4" />
              </button>
              <button
                class="rounded-lg p-2 text-xs font-medium transition-colors"
                :class="confirming === `${user.user_id}:delete` ? 'bg-red-500 px-2.5 text-white' : 'text-muted hover:bg-red-500/10 hover:text-red-500'"
                :title="confirming === `${user.user_id}:delete` ? undefined : 'Nebenstelle entfernen'"
                :disabled="busy"
                @click="remove(user)"
              >
                <span v-if="confirming === `${user.user_id}:delete`">Entfernen?</span>
                <Trash2 v-else class="h-4 w-4" />
              </button>
            </template>
            <button
              v-else-if="user.in_keycloak"
              class="inline-flex items-center gap-1.5 rounded-lg bg-cyan-500/15 px-3 py-1.5 text-xs font-medium text-brand ring-1 ring-cyan-500/25 transition-colors hover:bg-cyan-500/25"
              @click="openEditor(user)"
            >
              <Plus class="h-3.5 w-3.5" /> Nebenstelle
            </button>
          </div>
        </div>

        <!-- Inline-Editor -->
        <form
          v-if="editing === user.user_id"
          class="mt-3 flex flex-wrap items-end gap-3 rounded-xl bg-raised p-3"
          @submit.prevent="save(user)"
        >
          <label class="w-28">
            <span class="mb-1 block text-xs text-muted">Durchwahl</span>
            <input
              v-model="form.extension"
              required
              inputmode="numeric"
              pattern="10[0-9]{2}"
              maxlength="4"
              title="1000–1099"
              class="tabular w-full rounded-lg border border-line bg-surface px-3 py-1.5 font-mono text-sm text-fg focus:border-cyan-500 focus:outline-none"
            />
          </label>
          <label class="min-w-[12rem] flex-1">
            <span class="mb-1 block text-xs text-muted">Angezeigter Name (Anrufer-ID)</span>
            <input
              v-model="form.display_name"
              maxlength="80"
              class="w-full rounded-lg border border-line bg-surface px-3 py-1.5 text-sm text-fg focus:border-cyan-500 focus:outline-none"
            />
          </label>
          <div class="flex gap-2">
            <button
              type="submit"
              class="rounded-lg bg-cyan-500 px-3.5 py-1.5 text-sm font-semibold text-navy-800 transition-colors hover:bg-cyan-400 disabled:opacity-40"
              :disabled="busy"
            >{{ user.sip ? 'Speichern' : 'Zuweisen' }}</button>
            <button type="button" class="rounded-lg px-3 py-1.5 text-sm text-muted hover:text-fg" @click="editing = null">Abbrechen</button>
          </div>
        </form>
      </li>
    </ul>
  </section>
</template>
