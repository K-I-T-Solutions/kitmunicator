import type { Component } from 'vue'
import { Contact, Phone, Settings, Users, Voicemail } from 'lucide-vue-next'

export interface NavItem {
  to: string
  label: string
  icon: Component
  /** Zähler am Eintrag, siehe navBadge() */
  badge?: 'voicemail'
}

export const NAV_ITEMS: NavItem[] = [
  { to: '/', label: 'Team', icon: Users },
  { to: '/dialer', label: 'Telefon', icon: Phone },
  { to: '/voicemail', label: 'Voicemail', icon: Voicemail, badge: 'voicemail' },
  { to: '/contacts', label: 'Kontakte', icon: Contact },
  { to: '/settings', label: 'Einstellungen', icon: Settings },
]

export function isActive(item: NavItem, path: string): boolean {
  return item.to === '/' ? path === '/' : path.startsWith(item.to)
}
