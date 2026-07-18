# syntax=docker/dockerfile:1
#
# ATHENA web frontend — production image (Phase 5, W1).
#
# Multi-stage Next.js build using `output: "standalone"` (next.config.mjs):
# deps → build → a minimal runtime that ships only the standalone server and
# static assets, running as an unprivileged user.

# ---- dependencies ----------------------------------------------------------
FROM node:20-slim AS deps
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm ci

# ---- build -----------------------------------------------------------------
FROM node:20-slim AS build
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
ENV NEXT_TELEMETRY_DISABLED=1
RUN npm run build

# ---- runtime ---------------------------------------------------------------
FROM node:20-slim AS runtime
WORKDIR /app
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    PORT=3000
RUN groupadd --gid 10002 web \
    && useradd --uid 10002 --gid web --no-create-home --shell /usr/sbin/nologin web

# Standalone server + static assets only (no node_modules, no source).
COPY --from=build --chown=web:web /app/.next/standalone ./
COPY --from=build --chown=web:web /app/.next/static ./.next/static
COPY --from=build --chown=web:web /app/public ./public

USER web
EXPOSE 3000
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD node -e "require('http').get('http://127.0.0.1:3000/',r=>process.exit(r.statusCode<500?0:1)).on('error',()=>process.exit(1))"
CMD ["node", "server.js"]
