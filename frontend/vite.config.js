import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:5000',
        changeOrigin: true
      },
      '/load': {
        target: 'http://localhost:5000',
        changeOrigin: true
      },
      '/save': {
        target: 'http://localhost:5000',
        changeOrigin: true
      },
      '/run': {
        target: 'http://localhost:5000',
        changeOrigin: true
      },
      '/update': {
        target: 'http://localhost:5000',
        changeOrigin: true
      },
      '/terminal': {
        target: 'http://localhost:5000',
        changeOrigin: true
      },
      '/python': {
        target: 'http://localhost:5000',
        changeOrigin: true
      }
    }
  }
})
