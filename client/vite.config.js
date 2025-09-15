import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

// 做法 A：API 走 /api，前端掛根目錄 /
// - dev: 透過 proxy 將 /api/、/auth/ 轉到後端（不 rewrite，保留 /api 前綴）
// - build: 直接輸出到 Backend/dist，給 FastAPI 掛載提供
export default defineConfig(({ mode }) => {
const env = loadEnv(mode, process.cwd(), '')
return {
plugins: [react()],
base: '/',
build: {
outDir: '../Backend/dist',
emptyOutDir: true,
assetsDir: 'assets',
},
server: {
allowedHosts: true,
host: true,
port: 5173,
proxy: {
'/api': {
target: env.VITE_API_BASE_URL || 'http://192.168.0.126:8500',
changeOrigin: true,
// 不要 rewrite，讓前端以 /api 前綴呼叫，後端也用 /api 提供
},
 // 開發模式下：/me 與 /logout 也要代理到後端（這兩條在正式環境為同網域根路徑）
 '/me': {
 target: env.VITE_API_BASE_URL || 'http://192.168.0.126:8500',
 changeOrigin: true,
 },
 '/logout': {
 target: env.VITE_API_BASE_URL || 'http://192.168.0.126:8500',
 changeOrigin: true,
 },
'/auth': {
target: env.VITE_AUTH_BASE_URL || 'https://85b1115c2522.ngrok-free.app',
changeOrigin: true,
secure: false,
// 不要 rewrite，/auth/* 會原樣轉送
},
},
},
}
})
