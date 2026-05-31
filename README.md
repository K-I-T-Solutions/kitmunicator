# KITmunicator

Internes WebRTC-Telefonsystem fuer K.I.T. Solutions: browserbasierte Softphone-Loesung mit SIP-Anbindung, Presence-System und CRM-Integration.

## Überblick

| Komponente | Technologie |
|---|---|
| Backend | FastAPI · Async SQLAlchemy · PostgreSQL |
| Frontend | Vue 3 · SIP.js 0.21 · Pinia |
| Telefonie | Asterisk 20 · PJSIP · WebRTC |
| Auth | Keycloak 26 (JWT, PKCE) |
| STUN/TURN | coturn |
| Proxy | Caddy (DEV) · Traefik (Prod) |
| Automation | n8n |

---

## Quick Start (DEV)

```bash
# 1. Repository klonen
git clone git@github.com:K-I-T-Solutions/kitmunicator.git
cd kitmunicator

# 2. Umgebungsvariablen anlegen
cp .env.example .env
# .env anpassen (Keycloak, Sipgate, TURN-Secret)

# 3. Caddy-Einträge eintragen (einmalig)
# Inhalt aus infra/nginx/nginx.conf ans Ende von /srv/infra/Caddyfile kopieren
docker exec caddy_reverse_proxy caddy reload --config /etc/caddy/Caddyfile

# 4. Stack starten
make dev-up

# 5. Datenbank initialisieren
make db-migrate
```

Nach dem Start erreichbar unter:

| URL | Service |
|---|---|
| https://kitmunicator.intern.phudevelopement.xyz | Frontend |
| https://api.kitmunicator.intern.phudevelopement.xyz/docs | API Swagger |
| https://sip.kitmunicator.intern.phudevelopement.xyz | Asterisk WSS |

---

## Architektur

```
Browser
  │  HTTPS / WSS
  ▼
Caddy (TLS-Terminierung)
  ├── kitmunicator.*     → kitmunicator_ui:5173
  ├── api.kitmunicator.* → kitmunicator_backend:8000
  │                           │  WebSocket /ws/presence
  │                           │  REST /telephony /contacts
  │                           │
  │                           ├── central_postgres (core_network)
  │                           ├── keycloak         (core_network)
  │                           └── kitmunicator_asterisk:8088 (ARI)
  │
  └── sip.kitmunicator.* → kitmunicator_asterisk:8089 (WS)
                               │  SIP/WebRTC
                               └── STUN/TURN: kitmunicator_coturn:3478

Keycloak → n8n → KITmunicator API + WorkmateOS + Keycloak Attributes
```

### Netzwerke

| Umgebung | Netzwerk | Postgres | Proxy |
|---|---|---|---|
| DEV (Cisco) | `core_network` (extern, shared) | `central_postgres` | Caddy |
| Prod (Hetzner) | `kitmunicator_net` (eigen) | eigene Instanz | Traefik |

---

## Konfiguration

Alle Variablen in `.env` (Vorlage: `.env.example`):

### Backend

| Variable | Beschreibung |
|---|---|
| `DATABASE_URL` | PostgreSQL-URL (`postgresql://user:pass@host/db`) |
| `KEYCLOAK_URL` | Keycloak-Basis-URL |
| `KEYCLOAK_REALM` | Realm-Name (z.B. `kit`) |
| `KEYCLOAK_CLIENT_ID` | Client-ID der App |
| `ASTERISK_ARI_URL` | ARI-Basis-URL (`http://asterisk:8088`) |
| `ASTERISK_ARI_USER` | ARI-Benutzername |
| `ASTERISK_ARI_SECRET` | ARI-Passwort |
| `WORKMATE_API_URL` | WorkmateOS API-URL |
| `WORKMATE_API_KEY` | WorkmateOS API-Key |

### Frontend (Vite `VITE_*`)

| Variable | Beschreibung |
|---|---|
| `VITE_KEYCLOAK_URL` | Keycloak-URL (Browser-seitig) |
| `VITE_KEYCLOAK_REALM` | Realm |
| `VITE_KEYCLOAK_CLIENT_ID` | Client-ID |
| `VITE_API_URL` | Backend-URL |
| `VITE_API_WS_URL` | Backend-URL für WebSocket (`wss://...`) |
| `VITE_SIP_DOMAIN` | SIP-Domain (z.B. `kitmunicator.intern.phudevelopement.xyz`) |
| `VITE_SIP_WS_SERVER` | Asterisk WSS-URL (`wss://sip.kitmunicator.*`) |
| `VITE_TURN_HOST` | coturn-Hostname |
| `VITE_TURN_USER` | TURN-Benutzername |
| `VITE_TURN_CREDENTIAL` | TURN-Passwort |

### Asterisk

| Variable | Beschreibung |
|---|---|
| `ASTERISK_PUBLIC_IP` | Öffentliche IP (für NAT/ICE) |
| `SIPGATE_USERNAME` | Sipgate-Account-ID |
| `SIPGATE_PASSWORD` | Sipgate-Passwort |

### coturn

| Variable | Beschreibung |
|---|---|
| `TURN_EXTERNAL_IP` | Öffentliche IP des TURN-Servers |
| `TURN_SECRET` | Shared Secret (`openssl rand -hex 32`) |

---

## Makefile

```bash
make dev-up          # DEV-Stack starten (core_network)
make dev-down        # DEV-Stack stoppen
make prod-up         # Prod-Stack starten
make prod-down       # Prod-Stack stoppen
make db-migrate      # Alembic: upgrade head
make db-reset        # Alembic: downgrade base + upgrade head
make db-shell        # psql-Shell in central_postgres
make backend-shell   # bash im Backend-Container
make asterisk-shell  # Asterisk CLI (asterisk -rvvv)
make logs            # Alle Logs (follow)
make logs-backend    # Backend-Logs (follow)
make logs-asterisk   # Asterisk-Logs (follow)
```

---

## Integration mit WorkmateOS

### Automatisches User-Onboarding (n8n)

Wenn ein neuer User in Keycloak angelegt wird, führt der Workflow `n8n-workflow.json` automatisch folgende Schritte aus:

1. **WorkmateOS** — Employee anlegen / verknüpfen (`POST /api/v1/employees`)
2. **KITmunicator** — SIP-Account mit zufälligem Passwort anlegen (`POST /telephony/accounts`)
3. **Keycloak** — User-Attribute setzen (`sip_extension`, `sip_username`)

**Workflow importieren:**
1. In n8n unter https://n8n.intern.phudevelopement.xyz öffnen
2. *New Workflow* → *Import from file* → `n8n-workflow.json` hochladen
3. Credentials anlegen: `Keycloak Webhook Secret` (Header-Auth)
4. ENV-Variablen in n8n setzen: `KEYCLOAK_URL`, `KEYCLOAK_REALM`, `KEYCLOAK_ADMIN_CLIENT_ID`, `KEYCLOAK_ADMIN_CLIENT_SECRET`, `WORKMATE_API_URL`, `WORKMATE_API_KEY`, `KITMUNICATOR_API_URL`
5. Workflow aktivieren

**Keycloak Event Listener einrichten:**
```
Keycloak Admin → Realm Settings → Events → Event Listeners
→ keycloak-webhook hinzufügen
→ Webhook URL: https://n8n.intern.phudevelopement.xyz/webhook/keycloak-user-created
→ Secret: WEBHOOK_SECRET aus .env
```

### Kontakte / CRM

Der Contacts-Router (`/contacts`) ist ein transparenter Proxy zur WorkmateOS CRM API mit lokalem 5-Minuten-Cache. Kontaktänderungen im CRM werden nach Ablauf des Cache oder per manuellem Aufruf von `DELETE /contacts/cache/invalidate` (Admin-Rolle) übernommen.

### SIP-Extension im JWT

Nach dem Onboarding enthält jeder Keycloak-Token folgende Custom Claims:

```json
{
  "sip_extension": "1001",
  "sip_username": "max.mustermann"
}
```

Diese können im Frontend direkt aus `auth.userProfile` gelesen werden.

---

## Prod-Deployment (Hetzner)

```bash
# Images bauen und in Registry pushen
docker build --target prod -t ghcr.io/k-i-t-solutions/kitmunicator-backend:latest ./backend
docker build --target prod \
  --build-arg VITE_KEYCLOAK_URL=https://login.kit-it-koblenz.de \
  --build-arg VITE_SIP_WS_SERVER=wss://sip.kitmunicator.kit-it-koblenz.de \
  # ... weitere VITE_* Args
  -t ghcr.io/k-i-t-solutions/kitmunicator-ui:latest ./frontend

docker push ghcr.io/k-i-t-solutions/kitmunicator-backend:latest
docker push ghcr.io/k-i-t-solutions/kitmunicator-ui:latest

# Auf dem Hetzner-Server
make prod-up
```

**Hetzner-Firewall** — folgende Ports müssen freigegeben sein:

| Port | Protokoll | Dienst |
|---|---|---|
| 80, 443 | TCP | Traefik (HTTP/HTTPS) |
| 5060 | UDP | SIP |
| 3478 | UDP + TCP | STUN/TURN |
| 10000–10200 | UDP | RTP Media |
| 49160–49200 | UDP | TURN Relay |

---

## Verzeichnisstruktur

```
kitmunicator/
├── backend/
│   ├── main.py              FastAPI App
│   ├── config.py            Pydantic Settings
│   ├── database.py          Async SQLAlchemy
│   ├── keycloak.py          JWT-Validierung + Abhängigkeiten
│   ├── telephony/           SIP-Accounts, CDR, Voicemail, ARI-Client
│   ├── presence/            WebSocket Presence-System
│   ├── contacts/            WorkmateOS CRM Proxy
│   └── alembic/             DB-Migrationen
├── frontend/
│   └── src/
│       ├── stores/          auth.ts (Keycloak), phone.ts (SIP.js)
│       ├── composables/     usePhone.ts
│       ├── views/           DialerView, ContactsView, SettingsView
│       └── components/      PresenceBadge, IncomingCallOverlay
├── infra/
│   ├── asterisk/            pjsip, http, extensions, voicemail, modules
│   └── coturn/              STUN/TURN Konfiguration
├── docker-compose.yml       Prod (Traefik, eigene Postgres)
├── docker-compose.dev.yml   DEV (core_network, central_postgres)
├── n8n-workflow.json        User-Onboarding Workflow
└── Makefile
```

---

## Einordnung

KITmunicator ist als interne Kommunikationsschicht im K.I.T.-Stack gedacht. Die Plattform verbindet Telefonie, Presence und CRM-Daten mit den bestehenden Business-Prozessen rund um WorkmateOS.
