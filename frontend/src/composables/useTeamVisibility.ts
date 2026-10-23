import { ref } from 'vue'

// Gleicher Schlüssel wie in der bisherigen Oberfläche – bestehende Auswahl bleibt erhalten
const STORAGE_KEY = 'kitmunicator:presence:visible'

function load(): Set<string> | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    return raw ? new Set(JSON.parse(raw) as string[]) : null
  } catch {
    return null
  }
}

// null = keine Auswahl gespeichert → alle sichtbar
const visibleIds = ref<Set<string> | null>(load())

function save(ids: Set<string>) {
  visibleIds.value = ids
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify([...ids]))
  } catch {
    // Auswahl gilt dann nur für diese Sitzung
  }
}

export function useTeamVisibility() {
  function isVisible(userId: string): boolean {
    return visibleIds.value === null || visibleIds.value.has(userId)
  }

  function toggle(userId: string, allIds: string[]) {
    const next = new Set(visibleIds.value ?? allIds)
    if (next.has(userId)) next.delete(userId)
    else next.add(userId)
    save(next)
  }

  function setAll(ids: string[]) {
    save(new Set(ids))
  }

  return { isVisible, toggle, setAll }
}
