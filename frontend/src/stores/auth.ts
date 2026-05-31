import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import Keycloak from 'keycloak-js'

const kc = new Keycloak({
  url: import.meta.env.VITE_KEYCLOAK_URL,
  realm: import.meta.env.VITE_KEYCLOAK_REALM,
  clientId: import.meta.env.VITE_KEYCLOAK_CLIENT_ID,
})

// Token alle 60 Sekunden prüfen – wenn < 30s verbleibend, refresh
const TOKEN_REFRESH_INTERVAL_MS = 60_000
const TOKEN_MIN_VALIDITY_SECONDS = 30

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(null)
  const userProfile = ref<Record<string, unknown> | null>(null)
  const isAuthenticated = ref(false)

  const userId = computed(() => userProfile.value?.sub as string | undefined)
  const username = computed(() => userProfile.value?.preferred_username as string | undefined)
  const displayName = computed(() => {
    const p = userProfile.value
    if (!p) return ''
    return ((p.given_name as string) + ' ' + (p.family_name as string)).trim() || (p.preferred_username as string)
  })

  async function init(): Promise<void> {
    const authenticated = await kc.init({
      pkceMethod: 'S256',
      checkLoginIframe: false,
    })

    if (authenticated) {
      _syncToken()
      _startRefreshLoop()
    } else {
      // Nicht eingeloggt → einmalig zu Keycloak weiterleiten
      kc.login({ redirectUri: window.location.origin + '/' })
    }
  }

  function login(): void {
    kc.login({ redirectUri: window.location.origin + '/' })
  }

  function logout(): void {
    kc.logout({ redirectUri: window.location.origin })
  }

  function _syncToken(): void {
    token.value = kc.token ?? null
    userProfile.value = kc.tokenParsed as Record<string, unknown> ?? null
    isAuthenticated.value = kc.authenticated ?? false
  }

  function _startRefreshLoop(): void {
    setInterval(async () => {
      try {
        const refreshed = await kc.updateToken(TOKEN_MIN_VALIDITY_SECONDS)
        if (refreshed) _syncToken()
      } catch {
        // Token abgelaufen – erneut einloggen
        kc.login()
      }
    }, TOKEN_REFRESH_INTERVAL_MS)
  }

  // Axios/fetch-Interceptor-Hilfsfunktion
  function getAuthHeader(): { Authorization: string } | Record<string, never> {
    return token.value ? { Authorization: `Bearer ${token.value}` } : {}
  }

  return {
    token,
    userProfile,
    isAuthenticated,
    userId,
    username,
    displayName,
    init,
    login,
    logout,
    getAuthHeader,
  }
})
