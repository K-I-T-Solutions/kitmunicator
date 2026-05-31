# ── Stage 1: Abhängigkeiten installieren ──────────────────────────────────────
FROM node:22-alpine AS deps

WORKDIR /app

COPY package.json package-lock.json* ./
# npm ci wenn lock-file vorhanden, sonst npm install (erster Build)
RUN if [ -f package-lock.json ]; then npm ci --frozen-lockfile; else npm install; fi


# ── Stage 2: Produktions-Build ────────────────────────────────────────────────
FROM node:22-alpine AS build

WORKDIR /app

COPY --from=deps /app/node_modules ./node_modules
COPY . .

ARG VITE_KEYCLOAK_URL
ARG VITE_KEYCLOAK_REALM
ARG VITE_KEYCLOAK_CLIENT_ID
ARG VITE_API_URL
ARG VITE_API_WS_URL
ARG VITE_SIP_DOMAIN
ARG VITE_SIP_WS_SERVER
ARG VITE_TURN_HOST
ARG VITE_TURN_USER
ARG VITE_TURN_CREDENTIAL

RUN npm run build


# ── Stage 3: Nginx Production Server ──────────────────────────────────────────
FROM nginx:1.27-alpine AS prod

# Nginx-Config für Vue SPA (alle Routen auf index.html)
COPY --from=build /app/dist /usr/share/nginx/html

RUN printf 'server {\n\
    listen 80;\n\
    root /usr/share/nginx/html;\n\
    index index.html;\n\
\n\
    # SPA-Fallback\n\
    location / {\n\
        try_files $uri $uri/ /index.html;\n\
    }\n\
\n\
    # Statische Assets lang cachen\n\
    location /assets/ {\n\
        expires 1y;\n\
        add_header Cache-Control "public, immutable";\n\
    }\n\
\n\
    # Kein Caching für index.html\n\
    location = /index.html {\n\
        add_header Cache-Control "no-cache, no-store, must-revalidate";\n\
    }\n\
\n\
    gzip on;\n\
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml image/svg+xml;\n\
}\n' > /etc/nginx/conf.d/default.conf

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD wget -qO- http://localhost/ || exit 1


# ── Stage 4: Dev-Image (Vite Dev Server) ──────────────────────────────────────
FROM node:22-alpine AS dev

WORKDIR /app

COPY --from=deps /app/node_modules ./node_modules
COPY . .

EXPOSE 5173

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD wget -qO- http://localhost:5173 || exit 1

CMD ["npm", "run", "dev"]
