import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig(({ mode }) => {
    const env = loadEnv(mode, process.cwd(), '')
        return {
            plugins: [react()],
            base: '/',
            build: {
                outDir: 'dist',
                emptyOutDir: true,
                assetsDir: 'assets',
            },
            server: {
                allowedHosts: true,
                host: true,
                port: 8400,
                proxy: {
                '/api': {
                    target: env.VITE_API_BASE_URL,
                    changeOrigin: true,
                },
                '/me': {
                    target: env.VITE_API_BASE_URL,
                    changeOrigin: true,
                },
                '/logout': {
                    target: env.VITE_API_BASE_URL,
                    changeOrigin: true,
                },
                '/auth': {
                    target: env.VITE_AUTH_BASE_URL,
                    changeOrigin: true,
                    secure: false,
                },
            },
        },
    }
})
