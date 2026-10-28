import react from '@vitejs/plugin-react'
import { defineConfig } from 'vitest/config'

// Where `npm run dev` in apps/api serves the REST API and the team MCP server.
const API_URL = process.env.API_URL ?? 'http://127.0.0.1:8000'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    // Forward API calls to the Python server, so the frontend calls the API on its own origin.
    proxy: {
      '/api': API_URL,
      '/mcp': API_URL,
    },
  },
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
  },
})
