import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// When VITE_API_URL is not set (local dev / preview), proxy all API calls to
// the live backend so the dev server never intercepts them with index.html.
const BACKEND = 'https://library-app-qtegugoc4a-ew.a.run.app'

const proxy = {
  '/api': { target: BACKEND, changeOrigin: true, secure: true },
  '/health': { target: BACKEND, changeOrigin: true, secure: true },
}

export default defineConfig({
  plugins: [react()],
  server: { proxy },   // npm run dev
  preview: { proxy },  // npm run preview
})
