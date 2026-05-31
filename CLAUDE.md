### 2. Was du implementieren sollst

**Backend:**
- `config.py`: Pydantic Settings mit allen ENV-Variablen
  (DATABASE_URL, KEYCLOAK_URL, KEYCLOAK_REALM, KEYCLOAK_CLIENT_ID,
   ASTERISK_ARI_URL, ASTERISK_ARI_USER, ASTERISK_ARI_SECRET,
   WORKMATE_API_URL, WORKMATE_API_KEY)
- `database.py`: Async SQLAlchemy + PostgreSQL
- `keycloak.py`: JWT-Validierung via Keycloak JWKS, get_current_user Dependency
- `telephony/models.py`: SipAccount, CallRecord (CDR), Voicemail Tabellen
- `telephony/router.py`: Endpoints für SIP-Account CRUD, CDR abrufen,
   Voicemail listing
- `telephony/service.py`: Asterisk ARI REST Client (httpx async)
   - SIP-Account anlegen/löschen via ARI
   - CDR aus Asterisk DB lesen
- `presence/models.py`: UserPresence Tabelle
  (user_id, status: available/busy/away/dnd, updated_at)
- `presence/router.py`: GET /presence/{user_id}, PUT /presence/me,
  WebSocket /ws/presence für Echtzeit-Updates
- `contacts/router.py`: Proxy zu WorkmateOS CRM API mit lokalem Cache
- `main.py`: FastAPI App mit allen Routers, CORS, Lifespan

**Frontend:**
- `stores/auth.ts`: Keycloak-JS Integration, Token-Refresh, User-Info
- `stores/phone.ts`: SIP.js UserAgent, Session-Management,
  Call-State (idle/calling/connected/incoming)
- `composables/usePhone.ts`: register(), call(target), hangup(),
  answer(), mute(), hold() — alles als Vue 3 Composable
- `App.vue`: Layout mit Sidebar + Topbar + Router-View +
  IncomingCallOverlay (global, immer sichtbar)
- `DialerView.vue`: Keypad + Call-State-Display + Recent Calls
  (nutze das HTML-Mockup als Referenz für das Design)
- `components/shared/PresenceBadge.vue`: Zeigt Online/Busy/Away/DND
  mit Farb-Dot, empfängt Updates via WebSocket

**Infra:**
- `infra/asterisk/pjsip.conf`: Vollständige WebRTC-fähige PJSIP Config
  - Transport: WSS (WebSocket Secure)
  - Codec: opus, g722, g711 (ulaw/alaw)
  - NAT: force_rport, ice_support=yes, media_use_received_transport=yes
  - Template-basierter Endpoint für einfaches User-Onboarding
- `infra/asterisk/http.conf`: HTTP Server auf Port 8088, TLS aktiviert
- `infra/asterisk/extensions.conf`: Basis-Dialplan
  - Interne Durchwahlen (10xx)
  - Externe Anrufe via SIP-Trunk (Sipgate)
  - Voicemail-Fallback
- `infra/coturn/turnserver.conf`: STUN/TURN Konfiguration

**Docker Compose:**
- Services: backend, ui, postgres, asterisk, coturn
- Networks: internal (backend ↔ asterisk), external (ui exposed)
- Volumes: asterisk-config, postgres-data
- Health Checks für alle Services
- `.env.example` mit allen benötigten Variablen und Kommentaren

**n8n Workflow (JSON):**
- Trigger: Keycloak User Created Webhook
- Action 1: WorkmateOS API — Employee anlegen/verknüpfen
- Action 2: KITmunicator API — SIP-Account anlegen
  (Username = Keycloak-Username, Passwort auto-generiert)
- Action 3: Keycloak — Attribute setzen (sip_extension)

**Makefile:**
```makefile
dev-up        # docker-compose.dev.yml starten
prod-up       # docker-compose.yml starten
backend-shell # in backend container
db-migrate    # alembic upgrade head
db-reset      # alembic downgrade base + upgrade head
logs          # docker compose logs -f
```

**README.md:**
- Kurze Projektbeschreibung
- Quick Start (make dev-up)
- Architektur-Übersicht
- Konfiguration (.env)
- Integration mit WorkmateOS

### 3. Wichtige Hinweise

- Alle Python-Files mit Type Hints
- Async everywhere im Backend (httpx, asyncpg)
- Vue 3 Composition API only, kein Options API
- TypeScript strict mode
- Kommentare auf Deutsch wo sinnvoll
- Fehlerbehandlung überall — keine unbehandelten Exceptions
- SIP.js Version: 0.21.x (npm: sip.js)
- Keycloak-JS Version: 24.x

### 4. Was du NICHT machen sollst
- Kein FreePBX, kein Kamailio — nur Asterisk direkt
- Kein Jitsi, kein eigener Media Server in Phase 1
- Kein eigenes Auth-System — alles über Keycloak
- Keine Klassen-basierten Vue-Komponenten
- Keine UI-Bibliotheken (kein Vuetify, kein Quasar) —
  Custom CSS mit den K.I.T.-Design-Tokens

Fang mit der Verzeichnisstruktur an, dann Backend-Core,
dann Asterisk-Config, dann Frontend-Grundstruktur.
Frage nach wenn etwas unklar ist.

### 5. Branding & Assets

**Logo:**
Das KITmunicator-Logo liegt unter `assets/kitmunicator_logo.png`.
Es zeigt Headset + Laptop + Smartphone + Schraubenzieher als Cyan
Line-Art auf Navy Background mit Orange-Akzent (Schraubenzieher).

**Typografie im UI — WICHTIG:**
Der Produktname wird immer so dargestellt:
  `<span class="brand-kit">KIT</span><span class="brand-munic">municator</span>`

CSS-Klassen sind in `frontend/src/assets/global.css` definiert:
  `.brand-kit`   → color: #06B6D4; font-family: 'Montserrat'; font-weight: 800;
  `.brand-munic` → color: #FFFFFF; font-family: 'Montserrat'; font-weight: 400;

Niemals "KITmunicator" als plain text in der UI — immer mit dieser
Zweifarb-Behandlung. KIT = Cyan (#06B6D4), municator = Weiß.

**Farbwerte exakt aus dem Logo (in tokens.css als CSS-Variablen):**
  --kit-navy:       #0A1628   /* Logo Background */
  --kit-cyan:       #06B6D4   /* Line-Art, KIT-Schriftzug */
  --kit-orange:     #FF6B35   /* Schraubenzieher-Akzent */
  --kit-blue:       #3B82F6   /* Secondary Blue */
  --kit-white:      #FFFFFF   /* municator-Schriftzug */

**Assets-Verzeichnis:**
  assets/
  ├── kitmunicator_logo.png       (Navy BG, mit Text — Hauptlogo)
  ├── kitmunicator_logo_dark.png  (Black BG Variante — fehlt noch, User liefert)
  ├── kitmunicator_icon.png       (nur Icon, kein Text, für Favicon — fehlt noch)
  └── kitmunicator_wordmark.svg   (KIT cyan + municator weiß, Montserrat, skalierbar)

**Montserrat einbinden:**
In `frontend/index.html` folgendes `<link>` im `<head>` ergänzen:
  <link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@400;800&display=swap" rel="stylesheet">

**Logo-Verwendung im UI:**
- Sidebar (`App.vue`): Schriftzug mit `.brand-kit`/`.brand-munic` Klassen
- AppTopbar.vue (wenn extrahiert): Logo links (32px Höhe) + Schriftzug
  → `<img src="/assets/kitmunicator_icon.png" height="32" />`
  → `<span class="brand-kit">KIT</span><span class="brand-munic">municator</span>`
- README.md: Logo oben zentriert eingebunden
- favicon: `assets/kitmunicator_icon.png`

**Tone & Feel:**
Professionell, technisch präzise, zugänglich. Der Schraubenzieher im Logo
ist Programm — KITmunicator ist ein Handwerkzeug für echte Arbeit.
Keine unnötigen Animationen. Funktional schön.
