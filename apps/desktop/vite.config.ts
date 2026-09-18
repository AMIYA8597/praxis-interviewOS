import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
// @ts-ignore
import electronVitePlugin from 'electron-vite'

export default defineConfig({
  plugins: [react(), electronVitePlugin()],
  build: {
    target: 'chrome120'  // Match Electron's Chromium version
  }
})
