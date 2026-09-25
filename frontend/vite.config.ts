import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
export default defineConfig({ plugins: [react(), tailwindcss()], build: { rollupOptions: { output: { manualChunks: { 'react-vendor':['react','react-dom','react-router-dom'], 'data-vendor':['@tanstack/react-query','@tanstack/react-table'], 'markdown':['react-markdown'] } } } }, server: { proxy: { '/api': process.env.API_PROXY_TARGET || 'http://127.0.0.1:8000' } } })
