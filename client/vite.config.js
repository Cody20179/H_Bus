import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const target = env.VITE_API_BASE_URL || 'http://192.168.0.126:8500'
  return {
    plugins: [react()],
    server: {
      allowedHosts: true, // 允許外部（如 ngrok）連線
      host: true, // = 0.0.0.0，允許 LAN 存取
      port: 5173,
      proxy: {
        '/api': {
          target,
          changeOrigin: true,
          rewrite: (p) => p.replace(/^\/api/, ''),
        },
      },
    },
  }
})
