import { defineConfig } from '@playwright/test';

const PORT = 4173;

export default defineConfig({
  testDir: 'e2e',
  fullyParallel: true,
  use: { baseURL: `http://localhost:${PORT}` },
  // Serves the production build (run `npm run build` first); the fixture API is the server itself.
  webServer: {
    command: 'node dist/web/server/server.mjs',
    url: `http://localhost:${PORT}/internal/health`,
    env: {
      PORT: String(PORT),
      NG_ALLOWED_HOSTS: 'localhost',
      ELIBRARY_API_ORIGIN: `http://127.0.0.1:${PORT}`,
    },
    reuseExistingServer: false,
  },
});
