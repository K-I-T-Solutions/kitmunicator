/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_KEYCLOAK_URL: string
  readonly VITE_KEYCLOAK_REALM: string
  readonly VITE_KEYCLOAK_CLIENT_ID: string
  readonly VITE_API_URL: string
  readonly VITE_API_WS_URL: string
  readonly VITE_SIP_DOMAIN: string
  readonly VITE_SIP_WS_SERVER: string
  readonly VITE_TURN_HOST: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
