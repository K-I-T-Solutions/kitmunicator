.PHONY: dev-up dev-down prod-up prod-down backend-shell db-migrate db-reset logs ps

COMPOSE_DEV  := docker compose -f docker-compose.dev.yml
COMPOSE_PROD := docker compose -f docker-compose.yml

# ── DEV ───────────────────────────────────────────────────────────────────────

dev-up:
	$(COMPOSE_DEV) up -d --build

dev-down:
	$(COMPOSE_DEV) down

dev-restart:
	$(COMPOSE_DEV) restart

# ── PROD ──────────────────────────────────────────────────────────────────────

prod-up:
	$(COMPOSE_PROD) up -d --build

prod-down:
	$(COMPOSE_PROD) down

prod-restart:
	$(COMPOSE_PROD) restart

# ── Datenbank ─────────────────────────────────────────────────────────────────

db-migrate:
	$(COMPOSE_DEV) exec kitmunicator_backend alembic upgrade head

db-reset:
	$(COMPOSE_DEV) exec kitmunicator_backend alembic downgrade base
	$(COMPOSE_DEV) exec kitmunicator_backend alembic upgrade head

db-shell:
	docker exec -it central_postgres psql -U kitmunicator -d kitmunicator

# ── Shells ────────────────────────────────────────────────────────────────────

backend-shell:
	$(COMPOSE_DEV) exec kitmunicator_backend bash

asterisk-shell:
	$(COMPOSE_DEV) exec kitmunicator_asterisk asterisk -rvvv

# ── Logs ──────────────────────────────────────────────────────────────────────

logs:
	$(COMPOSE_DEV) logs -f

logs-backend:
	$(COMPOSE_DEV) logs -f kitmunicator_backend

logs-asterisk:
	$(COMPOSE_DEV) logs -f kitmunicator_asterisk

# ── Status ────────────────────────────────────────────────────────────────────

ps:
	$(COMPOSE_DEV) ps
