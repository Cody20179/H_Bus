import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  base: '/home/',           
  plugins: [vue()],
  server: {
    host: '0.0.0.0', 
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
