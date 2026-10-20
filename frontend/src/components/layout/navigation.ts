import type { Component } from 'vue'
import { Contact, Phone, Settings, Users } from 'lucide-vue-next'

export interface NavItem {
  to: string
  label: string
  icon: Component
}

// Voicemail folgt, sobald die Seite portiert ist
export const NAV_ITEMS: NavItem[] = [
  { to: '/', label: 'Team', icon: Users },
  { to: '/dialer', label: 'Telefon', icon: Phone },
  { to: '/contacts', label: 'Kontakte', icon: Contact },
  { to: '/settings', label: 'Einstellungen', icon: Settings },
]

export function isActive(item: NavItem, path: string): boolean {
  return item.to === '/' ? path === '/' : path.startsWith(item.to)
}
