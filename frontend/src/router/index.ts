import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = createRouter({
  history: createWebHistory(),
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
