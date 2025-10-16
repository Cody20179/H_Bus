import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [vue()],
  server: {
    host: '0.0.0.0', // 允許 LAN 存取
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8500', // 修改為 localhost
        changeOrigin: true,
        secure: false,
        // 保留 /api 前綴，因為您的後端 API 路徑是 /api/dashboard/*
      },
      '/auth': {
        target: 'http://localhost:8500', // 修改為 localhost
        changeOrigin: true,
        secure: false,
        // 處理 /auth 路徑的代理
      },
      '/users': {
        target: 'http://localhost:8500', // 修改為 localhost
        changeOrigin: true,
        secure: false,
        // 處理 /users 路徑的代理（會員管理）
      },
      '/Create_users': {              // 新增這段
      target: 'http://localhost:8500',
      changeOrigin: true,
     },
      '/All_Route': {
        target: 'http://localhost:8500',
        changeOrigin: true,
        secure: false,
        // 處理 /All_Route 路徑的代理（路線管理）
      },
      '/Route_Stations': {
        target: 'http://localhost:8500',
        changeOrigin: true,
        secure: false,
        // 處理 /Route_Stations 路徑的代理（路線站點查詢）
      },
    },
  },
  resolve: {
    alias: {
      '@': '/src',
    },
  },
})
