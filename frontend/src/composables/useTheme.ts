import { ref } from 'vue'

export type Theme = 'dark' | 'light'

const STORAGE_KEY = 'kitmunicator:theme'

// index.html setzt die Klasse bereits vor dem ersten Rendern
const theme = ref<Theme>(document.documentElement.classList.contains('dark') ? 'dark' : 'light')

function apply(next: Theme) {
  theme.value = next
  document.documentElement.classList.toggle('dark', next === 'dark')
  try {
    localStorage.setItem(STORAGE_KEY, next)
  } catch {
    // Privater Modus o. ä. – Theme gilt dann nur für diese Sitzung
  }
}

export function useTheme() {
  function toggle() {
    apply(theme.value === 'dark' ? 'light' : 'dark')
  }

  return { theme, toggle }
}
