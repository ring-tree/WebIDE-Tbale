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
      '/run': {
        target: 'http://localhost:5000', // 后端 Flask 服务器地址
        changeOrigin: true // 修改请求头中的 Origin 为目标地址
      },
      '/update': {
        target: 'http://localhost:5000', // 后端 Flask 服务器地址
        changeOrigin: true // 修改请求头中的 Origin 为目标地址
      },
      '/save': {
        target: 'http://localhost:5000', // 后端 Flask 服务器地址
        changeOrigin: true // 修改请求头中的 Origin 为目标地址
      },
      '/load': {
        target: 'http://localhost:5000', // 后端 Flask 服务器地址
        changeOrigin: true // 修改请求头中的 Origin 为目标地址
      },
      '/files': {
        target: 'http://localhost:5000', // 后端 Flask 服务器地址
        changeOrigin: true // 修改请求头中的 Origin 为目标地址
      },
      '/terminal/execute': {
        target: 'http://localhost:5000', // 后端 Flask 服务器地址
        changeOrigin: true // 修改请求头中的 Origin 为目标地址
      },
      '/python/version': {
        target: 'http://localhost:5000', // 后端 Flask 服务器地址
        changeOrigin: true // 修改请求头中的 Origin 为目标地址
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
