import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = createRouter({
  history: createWebHistory(),
  // Sprungmarken wie /settings#ansage; main ist der Scroll-Container, daher per scrollIntoView
  scrollBehavior(to) {
    if (to.hash) setTimeout(() => document.querySelector(to.hash)?.scrollIntoView({ behavior: 'smooth' }), 300)
  },
  routes: [
    {
      path: '/',
      name: 'home',
      component: () => import('@/views/HomeView.vue'),
      meta: { requiresAuth: true, title: 'Team' },
    },
    {
      path: '/dialer',
      name: 'dialer',
      component: () => import('@/views/DialerView.vue'),
      meta: { requiresAuth: true, title: 'Telefon' },
    },
    {
      path: '/voicemail',
      name: 'voicemail',
      component: () => import('@/views/VoicemailView.vue'),
      meta: { requiresAuth: true, title: 'Voicemail' },
    },
    {
      path: '/contacts',
      name: 'contacts',
      component: () => import('@/views/ContactsView.vue'),
      meta: { requiresAuth: true, title: 'Kontakte' },
    },
    {
      path: '/settings',
      name: 'settings',
      component: () => import('@/views/SettingsView.vue'),
      meta: { requiresAuth: true, title: 'Einstellungen' },
    },
  ],
})

router.beforeEach((to) => {
  const auth = useAuthStore()
  if (to.meta.requiresAuth && !auth.isAuthenticated) {
    // init() hat den Login bereits ausgelöst – hier nur blockieren
    return false
  }
})

export default router
