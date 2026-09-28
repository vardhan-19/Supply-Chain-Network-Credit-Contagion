import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

/**
 * vite.config.js
 *
 * Key improvements:
 *  - proxyTimeout / timeout: prevents Vite from printing ECONNREFUSED
 *    stack traces while the backend is warming up.
 *  - configure(proxy): silences connection-refused noise during startup.
 *  - /health added to proxy map for startup polling.
 */
export default defineConfig({
  plugins: [react()],
  server: {
    // Use a fixed port so the URL is always the same
    port: 5173,
    strictPort: false,        // fall back to next available port if 5173 is taken
    proxy: {
      '/health': {
        target: 'http://localhost:8001',
        changeOrigin: true,
        proxyTimeout: 2000,
        timeout: 2000,
        configure: (proxy) => {
          // Suppress ECONNREFUSED errors in the terminal during backend startup
          proxy.on('error', () => {});
        },
      },
      '/graph': {
        target: 'http://localhost:8001',
        changeOrigin: true,
        proxyTimeout: 30000,
        timeout: 30000,
        configure: (proxy) => {
          proxy.on('error', () => {});
        },
      },
      '/predict': {
        target: 'http://localhost:8001',
        changeOrigin: true,
        proxyTimeout: 30000,
        timeout: 30000,
        configure: (proxy) => {
          proxy.on('error', () => {});
        },
      },
      '/simulate': {
        target: 'http://localhost:8001',
        changeOrigin: true,
        proxyTimeout: 60000,
        timeout: 60000,
        configure: (proxy) => {
          proxy.on('error', () => {});
        },
      },
    },
  },
})
