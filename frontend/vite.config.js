import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// // https://vite.dev/config/
// export default defineConfig({
//   plugins: [vue()],
// })

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [vue()],
  server: {
    // 关键配置：设置代理
    proxy: {
      // 代理 /run 和 /update 请求到 Flask 后端
      '/api/files': {
        target: 'http://localhost:5000',
        changeOrigin: true
      },
      '/api/files/create': {
        target: 'http://localhost:5000',
        changeOrigin: true
      },
      '/api/files/delete': {
        target: 'http://localhost:5000',
        changeOrigin: true
      },
      '/api/files/rename': {
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
      '/save': {
        target: 'http://localhost:5000',
        changeOrigin: true
      },
      '/load': {
        target: 'http://localhost:5000',
        changeOrigin: true
      },
      '/terminal/execute': {
        target: 'http://localhost:5000',
        changeOrigin: true
      },
      '/python/version': {
        target: 'http://localhost:5000',
        changeOrigin: true
      },
      '/api': {
        target: 'http://localhost:5000',
        changeOrigin: true
      }
    }
  },
  build: {
    // 生产环境构建配置
    outDir: 'dist', // 输出目录
    minify: 'terser', // 使用terser进行代码压缩
    sourcemap: false, // 生产环境不生成sourcemap
    rollupOptions: {
      output: {
        // 打包优化
        manualChunks: {
          vendor: ['vue'],
          monaco: ['monaco-editor']
        }
      }
    }
  }
})
