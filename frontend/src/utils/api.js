/**
 * 统一的后端请求封装。
 *
 * 职责：
 *   1. 为每个浏览器会话生成稳定 ID，通过 X-Session-Id 头传给后端，
 *      使不同标签页 / 用户的数据集互相隔离（后端按会话分目录存放）。
 *   2. 集中处理请求头，避免各组件各写一套。
 *
 * 说明：访问令牌（X-Auth-Token）不在这里注入 —— 它由 Vite 开发代理
 *      在服务端注入，浏览器端不持有令牌。
 */

const SESSION_KEY = 'webide.sessionId'

/** 获取（必要时创建）当前浏览器会话 ID */
export function getSessionId() {
  let id = null
  try {
    id = window.localStorage.getItem(SESSION_KEY)
  } catch {
    // localStorage 不可用（隐私模式等）时退化为内存态
  }

  if (!id) {
    id = `sess-${Math.random().toString(36).slice(2, 10)}${Date.now().toString(36)}`
    try {
      window.localStorage.setItem(SESSION_KEY, id)
    } catch {
      // 忽略写入失败
    }
  }
  return id
}

/** 带会话标识的 fetch */
export function apiFetch(url, options = {}) {
  const headers = {
    'X-Session-Id': getSessionId(),
    ...(options.headers || {})
  }
  return fetch(url, { ...options, headers })
}

/** 读取 JSON 响应，非 2xx 时抛出带后端 message 的错误 */
export async function apiJson(url, options = {}) {
  const res = await apiFetch(url, options)
  let body = null
  try {
    body = await res.json()
  } catch {
    throw new Error(`服务返回了非 JSON 响应（HTTP ${res.status}）`)
  }

  if (!res.ok) {
    throw new Error(body?.message || `请求失败（HTTP ${res.status}）`)
  }
  return body
}
