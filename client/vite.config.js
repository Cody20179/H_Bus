import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')

  return {
    plugins: [react()],
    server: {
      allowedHosts: true,   // 允許 ngrok 進來
      host: true,           // = 0.0.0.0，允許 LAN 存取
      port: 5173,
      proxy: {
        // 後端 H_Bus API (本機 8500)
        '/api': {
          target: env.VITE_API_BASE_URL || 'http://192.168.0.126:8500',
          changeOrigin: true,
          rewrite: (p) => p.replace(/^\/api/, ''),
        },
        // Line Auth API (ngrok 公網)
        '/auth': {
          target: 'https://3f918fa9866f.ngrok-free.app',
          changeOrigin: true,
          secure: false, // 跳過 SSL 憑證驗證（ngrok 必須加這個）
          rewrite: (p) => p.replace(/^\/auth/, ''),
        },
      },
    },
  }
})
