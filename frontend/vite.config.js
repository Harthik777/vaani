import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  base: "./",  // the build is also served by the backend at /app/
  server: { port: 5173 },
})
