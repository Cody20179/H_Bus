import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    host: true, // = 0.0.0.0，允許 LAN 存取
    port: 5173
  }
})
