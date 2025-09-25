import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

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
                },
                '/me': {
                    target: env.VITE_API_BASE_URL || 'http://192.168.0.126:8500',
                    changeOrigin: true,
                },
                '/logout': {
                    target: env.VITE_API_BASE_URL || 'http://192.168.0.126:8500',
                    changeOrigin: true,
                },
                '/auth': {
                    target: env.VITE_AUTH_BASE_URL || 'https://fb247265dab7.ngrok-free.app',
                    changeOrigin: true,
                    secure: false,
                },
            },
        },
    }
})
