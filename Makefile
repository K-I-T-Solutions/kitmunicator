.DEFAULT_GOAL := help

COMPOSE_DEV  := docker compose -f docker-compose.dev.yml
COMPOSE_PROD := docker compose -f docker-compose.yml
ASTERISK     := docker exec kitmunicator_asterisk asterisk -rx

.PHONY: help \
	dev-up dev-start dev-stop dev-down dev-restart dev-ui-rebuild backend-recreate \
	prod-up prod-down prod-restart \
	db-migrate db-reset db-shell \
	backend-shell asterisk-shell asterisk-reload asterisk-status \
	logs logs-backend logs-asterisk logs-ui typecheck ps

help: ## Diese Übersicht
	@grep -hE '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

# ── DEV ───────────────────────────────────────────────────────────────────────

dev-up: ## Dev-Stack bauen und starten
	$(COMPOSE_DEV) up -d --build

dev-start: ## Dev-Stack starten ohne Neubau
	$(COMPOSE_DEV) up -d

dev-stop: ## Dev-Stack anhalten (Container bleiben)
	$(COMPOSE_DEV) stop

dev-down: ## Dev-Stack herunterfahren (Volumes bleiben)
	$(COMPOSE_DEV) down

dev-restart: ## Alle Dev-Container neu starten
	$(COMPOSE_DEV) restart

dev-ui-rebuild: ## UI neu bauen inkl. node_modules-Volume (nach npm-Änderungen)
	$(COMPOSE_DEV) up -d --build -V kitmunicator_ui

backend-recreate: ## Backend neu erstellen (nötig nach .env-Änderungen)
	$(COMPOSE_DEV) up -d --force-recreate kitmunicator_backend

# ── PROD ──────────────────────────────────────────────────────────────────────

prod-up: ## Prod-Stack bauen und starten
	$(COMPOSE_PROD) up -d --build

prod-down: ## Prod-Stack herunterfahren
	$(COMPOSE_PROD) down

prod-restart: ## Alle Prod-Container neu starten
	$(COMPOSE_PROD) restart

# ── Datenbank ─────────────────────────────────────────────────────────────────

db-migrate: ## Alembic-Migrationen ausführen
	$(COMPOSE_DEV) exec kitmunicator_backend alembic upgrade head

db-reset: ## Datenbank zurücksetzen (alle Daten weg!)
	$(COMPOSE_DEV) exec kitmunicator_backend alembic downgrade base
	$(COMPOSE_DEV) exec kitmunicator_backend alembic upgrade head

db-shell: ## psql auf der KITmunicator-Datenbank
	docker exec -it central_postgres psql -U kitmunicator -d kitmunicator

# ── Shells ────────────────────────────────────────────────────────────────────

backend-shell: ## Bash im Backend-Container
	$(COMPOSE_DEV) exec kitmunicator_backend bash

asterisk-shell: ## Asterisk-CLI
	$(COMPOSE_DEV) exec kitmunicator_asterisk asterisk -rvvv

# ── Asterisk ──────────────────────────────────────────────────────────────────

# Die Konfiguration wird nur beim Container-Start aus infra/asterisk kopiert;
# .tmpl-Dateien (rtp, res_pgsql) bleiben unberührt.
asterisk-reload: ## infra/asterisk/*.conf übernehmen und neu laden (ohne Neustart)
	docker exec -u root kitmunicator_asterisk sh -c 'cp /etc/asterisk-tpl/*.conf /etc/asterisk/ && chown asterisk:asterisk /etc/asterisk/*.conf'
	$(ASTERISK) 'core reload'

asterisk-status: ## Registrierte Nebenstellen und laufende Anrufe
	@$(ASTERISK) 'pjsip show endpoints' | grep -E 'Endpoint:|Contact:' | grep -v '<'
	@$(ASTERISK) 'core show channels concise' | grep . || echo "Keine laufenden Anrufe"

# ── Logs ──────────────────────────────────────────────────────────────────────

logs: ## Alle Logs verfolgen
	$(COMPOSE_DEV) logs -f

logs-backend: ## Backend-Logs verfolgen
	$(COMPOSE_DEV) logs -f kitmunicator_backend

logs-asterisk: ## Asterisk-Logs verfolgen
	$(COMPOSE_DEV) logs -f kitmunicator_asterisk

logs-ui: ## UI-Logs verfolgen
	$(COMPOSE_DEV) logs -f kitmunicator_ui

# ── Prüfen ────────────────────────────────────────────────────────────────────

typecheck: ## Frontend-Typecheck (im UI-Container, dort liegen die node_modules)
	$(COMPOSE_DEV) exec kitmunicator_ui npx vue-tsc --noEmit

# ── Status ────────────────────────────────────────────────────────────────────

ps: ## Status der Dev-Container
	$(COMPOSE_DEV) ps
