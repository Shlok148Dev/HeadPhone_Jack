# syntax=docker/dockerfile:1.7
# Build context: repository root.
FROM node:26-slim AS build
RUN corepack enable
WORKDIR /repo
COPY package.json pnpm-workspace.yaml pnpm-lock.yaml .npmrc tsconfig.base.json ./
COPY apps/realtime/package.json apps/realtime/
RUN --mount=type=cache,target=/root/.local/share/pnpm/store pnpm install --frozen-lockfile --filter @jingle/realtime...
COPY apps/realtime apps/realtime
RUN pnpm --filter @jingle/realtime build && pnpm --filter @jingle/realtime deploy --prod --legacy /out

FROM node:26-slim
WORKDIR /app
COPY --from=build /out ./
USER node
EXPOSE 4000
HEALTHCHECK --interval=10s --timeout=3s --retries=12 CMD node -e "fetch('http://127.0.0.1:4000/healthz').then(r=>process.exit(r.ok?0:1)).catch(()=>process.exit(1))"
CMD ["node", "dist/index.js"]
