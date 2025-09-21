import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  define: {
    // Make environment variables available at build time
    'process.env': process.env
  },
  server: {
    port: 5173,
    host: true
  }
})
