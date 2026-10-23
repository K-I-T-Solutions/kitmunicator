import type { Component } from 'vue'
import { Contact, Phone, Settings, ShieldCheck, Users, Voicemail } from 'lucide-vue-next'

export interface NavItem {
  to: string
  label: string
  icon: Component
  /** Zähler am Eintrag, siehe navBadge() */
  badge?: 'voicemail'
  /** Nur mit Rolle telephony_admin; mobil über die Einstellungen erreichbar */
  adminOnly?: boolean
}

export const NAV_ITEMS: NavItem[] = [
  { to: '/', label: 'Team', icon: Users },
  { to: '/dialer', label: 'Telefon', icon: Phone },
  { to: '/voicemail', label: 'Voicemail', icon: Voicemail, badge: 'voicemail' },
  { to: '/contacts', label: 'Kontakte', icon: Contact },
  { to: '/settings', label: 'Einstellungen', icon: Settings },
  { to: '/admin', label: 'Verwaltung', icon: ShieldCheck, adminOnly: true },
]

export function isActive(item: NavItem, path: string): boolean {
  return item.to === '/' ? path === '/' : path.startsWith(item.to)
}
