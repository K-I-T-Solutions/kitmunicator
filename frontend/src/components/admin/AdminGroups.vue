<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { CircleAlert, Pencil, PhoneIncoming, Plus, Trash2, UsersRound } from 'lucide-vue-next'
import { useAdmin, type RingGroup, type RingGroupInput } from '@/composables/useAdmin'
import UserAvatar from '@/components/ui/UserAvatar.vue'

const admin = useAdmin()
const groups = ref<RingGroup[]>([])
const loadState = ref<'loading' | 'ready' | 'error'>('loading')
const notice = ref<{ kind: 'ok' | 'error'; text: string } | null>(null)
const busy = ref(false)
const confirmDelete = ref<number | null>(null)

/** Alle Nebenstellen als mögliche Mitglieder/Weiterleitungsziele */
const accounts = computed(() =>
  admin.users.value
    .filter(u => u.sip)
    .map(u => ({ id: u.sip!.id, extension: u.sip!.extension, name: u.sip!.display_name || u.display_name, active: u.sip!.is_active }))
    .sort((a, b) => a.extension.localeCompare(b.extension)),
)

async function load() {
  try {
    const [list] = await Promise.all([admin.loadGroups(), admin.loadUsers()])
    groups.value = list
    loadState.value = 'ready'
  } catch {
    loadState.value = 'error'
  }
}

// ── Formular (neu oder bearbeiten) ───────────────────────────────────────────
const editingId = ref<number | 'new' | null>(null)
const form = reactive<RingGroupInput & { fallback_mode: 'hangup' | 'forward' }>({
  name: '', extension: '', ring_timeout: 25, fallback_extension: null,
  inbound_number: null, inbound_catch_all: false, member_ids: [], fallback_mode: 'hangup',
})

async function openForm(group?: RingGroup) {
  notice.value = null
  confirmDelete.value = null
  Object.assign(form, group
    ? {
        name: group.name, extension: group.extension, ring_timeout: group.ring_timeout,
        fallback_extension: group.fallback_extension, inbound_number: group.inbound_number,
        inbound_catch_all: group.inbound_catch_all, member_ids: group.members.map(m => m.id),
        fallback_mode: group.fallback_extension ? 'forward' : 'hangup',
      }
    : {
        name: '', extension: (await admin.nextGroupExtension()) ?? '', ring_timeout: 25, fallback_extension: null,
        inbound_number: null, inbound_catch_all: false, member_ids: [], fallback_mode: 'hangup',
      })
  editingId.value = group?.id ?? 'new'
}

function toggleMember(id: number) {
  form.member_ids = form.member_ids.includes(id) ? form.member_ids.filter(m => m !== id) : [...form.member_ids, id]
}

async function save() {
  busy.value = true
  notice.value = null
  const { fallback_mode, ...input } = form
  input.fallback_extension = fallback_mode === 'forward' ? input.fallback_extension : null
  try {
    const saved = await admin.saveGroup(input, editingId.value === 'new' ? undefined : (editingId.value as number))
    notice.value = { kind: 'ok', text: `Gruppe „${saved.name}“ (${saved.extension}) gespeichert.` }
    editingId.value = null
    groups.value = await admin.loadGroups()
  } catch (err) {
    notice.value = { kind: 'error', text: err instanceof Error ? err.message : String(err) }
  } finally {
    busy.value = false
  }
}

async function remove(group: RingGroup) {
  if (confirmDelete.value !== group.id) {
    confirmDelete.value = group.id
    return
  }
  busy.value = true
  try {
    await admin.deleteGroup(group.id)
    notice.value = { kind: 'ok', text: `Gruppe „${group.name}“ entfernt.` }
    groups.value = await admin.loadGroups()
  } catch (err) {
    notice.value = { kind: 'error', text: err instanceof Error ? err.message : String(err) }
  } finally {
    busy.value = false
    confirmDelete.value = null
  }
}

function fallbackLabel(group: RingGroup): string {
  if (!group.fallback_extension) return 'auflegen'
  const name = accounts.value.find(a => a.extension === group.fallback_extension)?.name
    ?? groups.value.find(g => g.extension === group.fallback_extension)?.name
  return `weiter an ${group.fallback_extension}${name ? ` (${name})` : ''}`
}

const fallbackTargets = computed(() => [
  ...accounts.value.map(a => ({ extension: a.extension, label: `${a.extension} · ${a.name} (inkl. Voicemail)` })),
  ...groups.value
    .filter(g => g.id !== editingId.value)
    .map(g => ({ extension: g.extension, label: `${g.extension} · Gruppe ${g.name}` })),
])

onMounted(load)
</script>

<template>
  <div class="space-y-4">
    <div class="flex flex-wrap items-center justify-between gap-3">
      <p class="text-sm text-muted">
        Unter der Gruppen-Durchwahl klingeln alle Mitglieder gleichzeitig. Eine Sipgate-Nummer leitet externe Anrufe direkt auf die Gruppe.
      </p>
      <button
        v-if="editingId === null"
        class="inline-flex items-center gap-1.5 rounded-lg bg-cyan-500 px-3.5 py-2 text-sm font-semibold text-navy-800 transition-colors hover:bg-cyan-400"
        @click="openForm()"
      >
        <Plus class="h-4 w-4" /> Neue Gruppe
      </button>
    </div>

    <p
      v-if="notice"
      class="text-sm"
      :class="notice.kind === 'ok' ? 'text-emerald-700 dark:text-emerald-300' : 'text-red-600 dark:text-red-400'"
      role="status"
    >{{ notice.text }}</p>

    <!-- Formular -->
    <form
      v-if="editingId !== null"
      class="space-y-4 rounded-2xl border border-cyan-500/40 bg-surface p-5"
      @submit.prevent="save"
    >
      <h3 class="text-sm font-semibold text-fg">{{ editingId === 'new' ? 'Neue Gruppe' : 'Gruppe bearbeiten' }}</h3>
      <div class="grid gap-3 sm:grid-cols-[1fr_8rem_8rem]">
        <label>
          <span class="mb-1 block text-xs text-muted">Name</span>
          <input v-model="form.name" required maxlength="100" placeholder="z. B. Support" class="w-full rounded-lg border border-line bg-app px-3 py-2 text-sm text-fg focus:border-cyan-500 focus:outline-none" />
        </label>
        <label>
          <span class="mb-1 block text-xs text-muted">Durchwahl</span>
          <input v-model="form.extension" required pattern="20[0-9]{2}" maxlength="4" title="2000–2099" inputmode="numeric" class="tabular w-full rounded-lg border border-line bg-app px-3 py-2 font-mono text-sm text-fg focus:border-cyan-500 focus:outline-none" />
        </label>
        <label>
          <span class="mb-1 block text-xs text-muted">Klingeldauer (s)</span>
          <input v-model.number="form.ring_timeout" type="number" min="5" max="120" required class="tabular w-full rounded-lg border border-line bg-app px-3 py-2 text-sm text-fg focus:border-cyan-500 focus:outline-none" />
        </label>
      </div>

      <fieldset>
        <legend class="mb-2 text-xs text-muted">Mitglieder <span class="text-subtle">({{ form.member_ids.length }})</span></legend>
        <p v-if="accounts.length === 0" class="text-sm text-subtle">Noch keine Nebenstellen vorhanden.</p>
        <div class="flex flex-wrap gap-2">
          <button
            v-for="a in accounts"
            :key="a.id"
            type="button"
            role="checkbox"
            :aria-checked="form.member_ids.includes(a.id)"
            class="flex items-center gap-2 rounded-full py-1 pl-1 pr-3 text-sm ring-1 transition-colors"
            :class="form.member_ids.includes(a.id) ? 'bg-cyan-500/15 text-fg ring-cyan-500/50' : 'bg-raised text-muted ring-transparent hover:text-fg'"
            @click="toggleMember(a.id)"
          >
            <UserAvatar :name="a.name" size="sm" />
            {{ a.name }} <span class="tabular font-mono text-xs text-subtle">{{ a.extension }}</span>
            <span v-if="!a.active" class="text-[10px] uppercase text-red-500">gesperrt</span>
          </button>
        </div>
      </fieldset>

      <fieldset class="grid gap-3 sm:grid-cols-2">
        <legend class="mb-2 text-xs text-muted">Wenn niemand abnimmt</legend>
        <select v-model="form.fallback_mode" class="rounded-lg border border-line bg-app px-3 py-2 text-sm text-fg focus:border-cyan-500 focus:outline-none">
          <option value="hangup">Auflegen</option>
          <option value="forward">Weiterleiten an …</option>
        </select>
        <select
          v-if="form.fallback_mode === 'forward'"
          v-model="form.fallback_extension"
          required
          class="rounded-lg border border-line bg-app px-3 py-2 text-sm text-fg focus:border-cyan-500 focus:outline-none"
        >
          <option :value="null" disabled>Ziel wählen</option>
          <option v-for="t in fallbackTargets" :key="t.extension" :value="t.extension">{{ t.label }}</option>
        </select>
      </fieldset>

      <fieldset class="space-y-2">
        <legend class="mb-2 text-xs text-muted">Eingehend über Sipgate</legend>
        <input
          v-model="form.inbound_number"
          placeholder="Rufnummer, z. B. +49 261 123456 (optional)"
          class="w-full rounded-lg border border-line bg-app px-3 py-2 text-sm text-fg focus:border-cyan-500 focus:outline-none sm:w-80"
        />
        <label class="flex items-center gap-2 text-sm text-fg">
          <input v-model="form.inbound_catch_all" type="checkbox" class="h-4 w-4 accent-cyan-500" />
          Alle übrigen eingehenden Anrufe (Hauptnummer)
        </label>
      </fieldset>

      <div class="flex gap-2">
        <button type="submit" class="rounded-lg bg-cyan-500 px-4 py-2 text-sm font-semibold text-navy-800 transition-colors hover:bg-cyan-400 disabled:opacity-40" :disabled="busy">Speichern</button>
        <button type="button" class="rounded-lg px-3 py-2 text-sm text-muted hover:text-fg" @click="editingId = null">Abbrechen</button>
      </div>
    </form>

    <!-- Liste -->
    <div v-if="loadState === 'loading'" class="space-y-3" aria-busy="true">
      <div v-for="n in 2" :key="n" class="h-28 animate-pulse rounded-2xl bg-surface" />
    </div>
    <div v-else-if="loadState === 'error'" class="flex flex-col items-center rounded-2xl border border-line/60 bg-surface py-12 text-center">
      <CircleAlert class="mb-2 h-6 w-6 text-subtle" />
      <p class="text-sm text-muted">Gruppen konnten nicht geladen werden.</p>
      <button class="mt-2 text-sm text-brand hover:underline" @click="load">Erneut versuchen</button>
    </div>
    <div v-else-if="groups.length === 0 && editingId === null" class="flex flex-col items-center rounded-2xl border border-dashed border-line py-12 text-center">
      <UsersRound class="mb-2 h-6 w-6 text-subtle" />
      <p class="text-sm text-muted">Noch keine Gruppen – z. B. „Support“ auf 2000.</p>
    </div>

    <ul v-else class="grid gap-3 md:grid-cols-2">
      <li v-for="g in groups" :key="g.id" class="rounded-2xl border border-line/60 bg-surface p-4">
        <div class="flex items-start gap-3">
          <span class="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-cyan-500/15 text-brand"><UsersRound class="h-5 w-5" /></span>
          <div class="min-w-0 flex-1">
            <p class="truncate text-sm font-semibold text-fg">{{ g.name }} <span class="tabular font-mono font-normal text-muted">{{ g.extension }}</span></p>
            <p class="text-xs text-subtle">{{ g.ring_timeout }} s klingeln, dann {{ fallbackLabel(g) }}</p>
          </div>
          <button class="rounded-lg p-2 text-muted hover:bg-raised hover:text-fg" aria-label="Bearbeiten" title="Bearbeiten" @click="openForm(g)">
            <Pencil class="h-4 w-4" />
          </button>
          <button
            class="rounded-lg p-2 text-xs font-medium transition-colors"
            :class="confirmDelete === g.id ? 'bg-red-500 px-2.5 text-white' : 'text-muted hover:bg-red-500/10 hover:text-red-500'"
            :disabled="busy"
            :title="confirmDelete === g.id ? undefined : 'Gruppe entfernen'"
            @click="remove(g)"
          >
            <span v-if="confirmDelete === g.id">Entfernen?</span>
            <Trash2 v-else class="h-4 w-4" />
          </button>
        </div>

        <div class="mt-3 flex flex-wrap gap-1.5">
          <span
            v-for="m in g.members"
            :key="m.id"
            class="rounded-full bg-raised px-2.5 py-1 text-xs"
            :class="m.is_active ? 'text-fg' : 'text-subtle line-through'"
          >{{ m.display_name || m.username }} <span class="tabular font-mono text-subtle">{{ m.extension }}</span></span>
          <span v-if="g.members.length === 0" class="text-xs text-amber-600 dark:text-amber-400">Keine Mitglieder – Anrufe gehen direkt zum Fallback.</span>
        </div>

        <p v-if="g.inbound_number || g.inbound_catch_all" class="mt-3 flex items-center gap-1.5 border-t border-line/40 pt-3 text-xs text-muted">
          <PhoneIncoming class="h-3.5 w-3.5 text-brand" />
          <template v-if="g.inbound_number">Sipgate <span class="font-mono">0{{ g.inbound_number }}</span></template>
          <template v-if="g.inbound_number && g.inbound_catch_all"> · </template>
          <template v-if="g.inbound_catch_all">Hauptnummer (alle übrigen Anrufe)</template>
        </p>
      </li>
    </ul>
  </div>
</template>
