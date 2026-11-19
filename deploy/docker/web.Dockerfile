# Angular SSR app on Node (D-39). Build context is the repository root.
FROM node:24-slim AS build
WORKDIR /src
COPY web/package.json web/package-lock.json ./
RUN npm ci --ignore-scripts
COPY web/ ./
RUN npx ng build

FROM node:24-slim
WORKDIR /app
COPY --from=build /src/dist/web ./dist/web
# why: the SSR server rejects Host headers that are not allow-listed (SSRF protection); set per environment.
ENV NODE_ENV=production PORT=4000 NG_ALLOWED_HOSTS=localhost
USER node
HEALTHCHECK --interval=10s --timeout=3s --start-period=10s --start-interval=1s --retries=3 \
  CMD node -e "fetch('http://127.0.0.1:4000/internal/health').then(r => process.exit(r.ok ? 0 : 1)).catch(() => process.exit(1))"
CMD ["node", "dist/web/server/server.mjs"]
