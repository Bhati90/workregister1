import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      // This will now correctly proxy any request starting with /api to your Django server
      '/api': {
        target: 'http://127.0.0.1:8000', // Your Django backend URL
        changeOrigin: true, // Necessary for the proxy to work correctly
      },
    },
  },
})
