import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  base: '/static/',
  plugins: [react()],
  build: {
    outDir: '../modules/web_ui/src/static',
    emptyOutDir: true
  },
  server: {
    host: '127.0.0.1',
    port: 5173,
    proxy: {
      '/api/': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true
      },
      '/ws/': {
        target: 'http://127.0.0.1:8000',
        ws: true,
        changeOrigin: true
      }
    }
  }
})
