# KITmunicator

Internes SIP/WebRTC-Kommunikationssystem für K.I.T. Solutions.

## Stack

- **Backend:** FastAPI + PostgreSQL + Alembic (async SQLAlchemy), Python 3.12
- **Frontend:** Vue 3 (Composition API), SIP.js 0.21.x, Vite dev server
- **UI:** Tailwind 3 + lucide-vue-next. Theme-Farben als CSS-Variablen (`--c-*`) in `frontend/src/assets/global.css`, Hell/Dunkel über `.dark` auf `<html>`. Schriften lokal via `@fontsource` (kein Google Fonts)
- **Telefonie:** Asterisk 20.x, PJSIP WebRTC (Port 8089), ARI via App `kitmunicator`
- **Auth:** Keycloak SSO, Realm `kit`, Client `kitmunicator`
- **Reverse Proxy:** Caddy → `sip.kitmunicator.intern.phudevelopement.xyz`

## Infra

- KITmunicator Backend + Asterisk auf cisco (192.168.178.x / Homelab)
- TURN: coturn auf 192.168.178.100:3478
- Aktueller Alembic-Stand: Migration 0005

## Abgeschlossene Features

- Presence ↔ Asterisk Sync via ARI WebSocket (ChannelCreated/StateChange/Destroyed)
- CDR-System: CallRecord bei ChannelDestroyed, caller_name + callee_name aus SipAccount-Lookup
- Voicemail (deutsche Sounds), Trunk-Channel-Tracking
- Voicemail im Web: Backend liest den Asterisk-Spool (Volume `asterisk_voicemail*`, im Backend read-only) und gleicht ihn bei `GET /telephony/voicemail` mit der DB ab (`telephony/voicemail_store.py`, Schlüssel `msg_id`). Kein Webhook mehr
- Automatisches SIP-Onboarding via n8n-Workflow (Dialplan dynamisch, ext-lookup Endpoint)
- Offboarding-Workflow (n8n-offboarding-workflow.json)
- Nextcloud Talk auf file-01 (cloud.kit-it-koblenz.de) mit Keycloak SSO + TURN
- Mattermost auf n8n-01 (chat.kit-it-koblenz.de) mit Keycloak SSO
- Netbird Zero Trust deployed (netbird.kit-it-koblenz.de), alle 5 Server im 100.99.0.0/16 Netz

## Bekannte Probleme

- `vm-theperson` Sounddatei fehlt → Voicemail-Ansage bricht ab
- ARI-Reconnect löscht `_active_channels` + `_pending_calls` → CDR-Verlust bei Reconnect
- CDR Master.csv Asterisk-Fehler (Verzeichnis fehlt) — eigenes CDR-System macht das irrelevant

## Branding

```css
--kit-navy:   #0A1628
--kit-cyan:   #06B6D4   /* KIT-Schriftzug */
--kit-orange: #FF6B35   /* Akzent */
--kit-blue:   #3B82F6
```

Produktname immer zweifarbig: `<span class="brand-kit">KIT</span><span class="brand-munic">municator</span>`
Nie als plain text. Klassen in `frontend/src/assets/global.css`.

## Netbird (Stand 2026-07-20)

`AUTH_REDIRECT_URI=/callback` (NICHT `/` — führt zu `storage[oidc.login] is empty` Bug)
