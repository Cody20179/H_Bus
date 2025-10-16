import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// https://vitejs.dev/config/
export default defineConfig({
  base: '/home/',            // 👈 這行是關鍵，所有靜態資源都走 /home
  plugins: [vue()],
  server: {
    host: '0.0.0.0',         // 允許 LAN 存取
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8600',
        changeOrigin: true,
        secure: false,
      },
      '/auth': {
        target: 'http://localhost:8600',
        changeOrigin: true,
        secure: false,
      },
      '/users': {
        target: 'http://localhost:8600',
        changeOrigin: true,
        secure: false,
      },
      '/Create_users': {
        target: 'http://localhost:8600',
        changeOrigin: true,
        secure: false,
      },
    },
  },
  resolve: {
    alias: {
      '@': '/src',
    },
  },
})
