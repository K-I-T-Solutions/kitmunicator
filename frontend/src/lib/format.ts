// Darstellungs-Helfer ohne App-Zustand

/** Sekunden als MM:SS */
export function formatDuration(seconds: number): string {
  const m = Math.floor(seconds / 60).toString().padStart(2, '0')
  const s = (seconds % 60).toString().padStart(2, '0')
  return `${m}:${s}`
}

/** "Joshua Phu Kuhrau" → "JK", "jessica" → "JE", "+49 151…" → "#" */
export function initials(name: string): string {
  const clean = name.trim()
  if (!clean || /^[+\d\s*#]+$/.test(clean)) return '#'
  const parts = clean.split(/[\s._-]+/).filter(Boolean)
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase()
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase()
}

const AVATAR_COLORS = ['#06B6D4', '#3B82F6', '#8B5CF6', '#EC4899', '#F97316', '#14B8A6', '#EAB308', '#6366F1']

/** Stabile Avatar-Farbe pro Name */
export function avatarColor(key: string): string {
  let hash = 0
  for (const ch of key) hash = (hash * 31 + ch.charCodeAt(0)) | 0
  return AVATAR_COLORS[Math.abs(hash) % AVATAR_COLORS.length]
}

const timeFmt = new Intl.DateTimeFormat('de-DE', { hour: '2-digit', minute: '2-digit' })
const dateFmt = new Intl.DateTimeFormat('de-DE', { day: '2-digit', month: '2-digit' })

/** "Heute 09:42", "Gestern 17:12", "14.10. 08:30" */
export function formatCallTime(iso: string): string {
  const date = new Date(iso)
  const today = new Date()
  const yesterday = new Date()
  yesterday.setDate(today.getDate() - 1)

  const sameDay = (a: Date, b: Date) => a.toDateString() === b.toDateString()
  const time = timeFmt.format(date)
  if (sameDay(date, today)) return `Heute ${time}`
  if (sameDay(date, yesterday)) return `Gestern ${time}`
  return `${dateFmt.format(date)} ${time}`
}
