import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import { useAuthStore } from './stores/auth'
import './assets/tokens.css'
import './assets/global.css'

const app = createApp(App)
const pinia = createPinia()

app.use(pinia)
app.use(router)

// Keycloak initialisieren, bevor die App gemountet wird
const auth = useAuthStore()
auth.init().then(() => {
  app.mount('#app')
})
