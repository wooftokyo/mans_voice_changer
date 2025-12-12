import path from 'path'
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react-swc'
import tailwindcss from '@tailwindcss/vite'
import { tanstackRouter } from '@tanstack/router-plugin/vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    tanstackRouter({
      target: 'react',
      autoCodeSplitting: true,
    }),
    react(),
    tailwindcss(),
  ],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 5173,
    proxy: {
      '/upload': {
        target: 'http://localhost:5003',
        changeOrigin: true,
      },
      '/upload_for_editor': {
        target: 'http://localhost:5003',
        changeOrigin: true,
      },
      '/apply_manual_pitch': {
        target: 'http://localhost:5003',
        changeOrigin: true,
      },
      '/status': {
        target: 'http://localhost:5003',
        changeOrigin: true,
      },
      '/download': {
        target: 'http://localhost:5003',
        changeOrigin: true,
      },
      '/audio': {
        target: 'http://localhost:5003',
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: '../static',
    emptyOutDir: true,
  },
})
