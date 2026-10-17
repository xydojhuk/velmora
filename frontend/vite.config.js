import { readFileSync } from 'node:fs'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// Shared root VERSION: resolved both on Fedora and in the Docker build image.
const version = readFileSync(new URL('../VERSION', import.meta.url), 'utf8').trim()
if (!/^[0-9]+\.[0-9]+\.[0-9]+(?:-[a-zA-Z0-9.-]+)?$/.test(version)) throw new Error('Invalid root VERSION')
export default defineConfig({
  define: { __VELMORA_VERSION__: JSON.stringify(version) },
  plugins: [vue()],
  build: {
    manifest: true
  },
  ssr: {
    noExternal: ['@unhead/vue']
  }
})
