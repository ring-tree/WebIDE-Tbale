import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const currentDir = path.dirname(fileURLToPath(import.meta.url))

const BACKEND_TARGET = 'http://localhost:5000'

// 后端访问令牌：由后端启动时生成于 backend/.webide_token
// 在代理层注入请求头，浏览器端不持有令牌，直接访问 5000 端口会被拒绝
function readAuthToken() {
  if (process.env.WEBIDE_AUTH_TOKEN) {
    return process.env.WEBIDE_AUTH_TOKEN
  }
  try {
    return fs.readFileSync(path.resolve(currentDir, '../backend/.webide_token'), 'utf-8').trim()
  } catch {
    return ''
  }
}

const PROXY_PATHS = ['/api', '/load', '/save', '/run', '/update', '/terminal', '/python']

function createProxy() {
  const proxy = {}
  for (const prefix of PROXY_PATHS) {
    proxy[prefix] = {
      target: BACKEND_TARGET,
      changeOrigin: true,
      configure: (proxyServer) => {
        // 每次请求时惰性读取令牌，避免前端先于后端启动时令牌缺失
        proxyServer.on('proxyReq', (proxyReq) => {
          const token = readAuthToken()
          if (token) {
            proxyReq.setHeader('X-Auth-Token', token)
          }
        })
      }
    }
  }
  return proxy
}

export default defineConfig({
  plugins: [vue()],
  server: {
    proxy: createProxy()
  }
})
