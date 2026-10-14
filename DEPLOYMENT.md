# WebIDE 部署指南

本指南说明如何部署 WebIDE-Tbale。

> ⚠️ **先读这一节**：本服务允许执行任意 Python 代码与白名单内的系统命令，
> 这是它的核心能力，也是它的主要风险。**默认配置仅适用于本机单用户使用**。
> 若要对外提供服务，请务必先阅读文末的[安全部署清单](#2-生产部署前的必要动作)。

---

## 目录结构

```
WebIDE-Tbale/
├── frontend/          # 前端 Vue 项目
│   └── dist/          # 前端构建输出（构建后生成）
├── backend/           # 后端 Flask 项目
│   ├── pyproject.toml # 依赖权威声明
│   ├── uv.lock        # 锁定版本
│   └── .venv/         # uv 创建的虚拟环境
├── config/            # 全局 AI 配置
│   └── ai_config.json
├── project/           # IDE 工作区（被编辑的目标目录）
├── package.json       # 根级编排脚本
└── start_both.bat     # Windows 一键启动（开发用）
```

---

## 环境要求

### 前端
- Node.js 18.0+（项目自带便携版位于 `node_env/`）
- npm 9.0+

### 后端
- Python **3.13**
- [uv](https://docs.astral.sh/uv/)（依赖与虚拟环境管理）

> 旧版文档要求 `pip install -r requirements.txt`，该方式**已废弃**：
> 根目录的 `requirements.txt` 现已改为指引文件，依赖统一由 `backend/pyproject.toml` 声明。

---

## 部署步骤

### 1. 获取代码

```bash
git clone <项目仓库地址>
cd WebIDE-Tbale
```

### 2. 安装依赖

```bash
# 后端：创建 backend/.venv 并安装全部依赖
cd backend && uv sync && cd ..

# 前端
cd frontend && npm install && cd ..
```

或使用根级脚本：`npm run install`

### 3. 配置 AI（可选）

编辑 `config/ai_config.json`，或更推荐地把密钥写在 `config/ai_config.local.json`：

```bash
cp config/ai_config.local.example.json config/ai_config.local.json
# 填入真实 api_key
```

**不要**把真实密钥写进 `config/ai_config.json` 并提交。也可用环境变量 `DASHSCOPE_API_KEY` 覆盖。

### 4. 构建前端

```bash
npm run build          # 产物位于 frontend/dist
```

### 5. 配置访问令牌

后端首次启动会自动生成令牌并写入 `backend/.webide_token`。
**所有 API 都要求 `X-Auth-Token` 请求头**，因此前端与后端之间的反向代理必须注入该头。

开发环境由 `frontend/vite.config.js` 自动完成注入；生产环境需要在 Nginx 层配置（见下）。

### 6. 部署后端

#### 方式 A：直接运行（小规模 / 内网）

```bash
cd backend
uv run python app.py
```

服务默认绑定 `127.0.0.1:5000`，可通过 `WEBIDE_HOST` / `WEBIDE_PORT` 调整。

#### 方式 B：WSGI 服务器（推荐用于生产）

Flask 自带服务器仅供开发。生产建议使用 waitress（Windows）或 gunicorn（Linux）：

```bash
# Windows
cd backend
uv add waitress
uv run python -c "from waitress import serve; from app import app; serve(app, host='127.0.0.1', port=5000, threads=8)"
```

```bash
# Linux
cd backend
uv add gunicorn
uv run gunicorn -w 4 -b 127.0.0.1:5000 app:app
```

> ⚠️ 多 worker 部署时请注意：`/run` 与 `/terminal/execute` 会派生子进程，
> 内存与并发限制按 worker 独立生效，总资源占用需按 worker 数放大评估。

### 7. 配置反向代理

前端静态资源与 API 由同一个 Nginx 提供，**关键是注入访问令牌**：

```nginx
server {
    listen 80;
    server_name your-domain.com;

    # 前端静态资源
    location / {
        root /path/to/WebIDE-Tbale/frontend/dist;
        index index.html;
        try_files $uri $uri/ /index.html;
    }

    # 后端 API —— 统一注入令牌，浏览器端不持有
    location ~ ^/(api|load|save|run|update|terminal|python) {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;

        # 令牌取自 backend/.webide_token（需保证 Nginx 可读该文件）
        proxy_set_header X-Auth-Token "<从 backend/.webide_token 读取的值>";

        # 代码执行可能耗时较长
        proxy_read_timeout 120s;
        client_max_body_size 50m;   # 与 WEBIDE_MAX_UPLOAD_MB 保持一致
    }
}
```

> 令牌是静态值，可直接写入 Nginx 配置并限制配置文件权限。
> 若使用环境变量，需在 `nginx.conf` 顶层声明 `env WEBIDE_AUTH_TOKEN;`。

### 8. 启动

```bash
# 开发环境（同时拉起前后端）
npm run dev-all

# 或分别启动
npm run server    # 后端
npm run dev       # 前端
```

生产环境：先启动 WSGI 服务器，再由 Nginx 提供静态资源与代理。

---

## 配置项

全部配置见 `.env.example`。后端启动时会自动加载项目根目录与 `backend/` 下的 `.env`。

### 关键配置

| 配置项 | 默认值 | 说明 |
|---|---|---|
| `WEBIDE_HOST` | `127.0.0.1` | 监听地址。改为 `0.0.0.0` 会暴露到局域网，启动时会打印警告 |
| `WEBIDE_PORT` | `5000` | 监听端口 |
| `WEBIDE_AUTH_TOKEN` | 自动生成 | 访问令牌，留空则生成到 `backend/.webide_token` |
| `WEBIDE_MAX_UPLOAD_MB` | `50` | 单个上传文件体积上限 |
| `WEBIDE_EXEC_TIMEOUT` | `30` | 代码/命令执行超时（秒） |
| `WEBIDE_EXEC_MEMORY_MB` | `1024` | 单进程内存上限（Windows 经 Job Object 施加） |
| `WEBIDE_EXEC_MAX_PROCS` | `32` | 并发子进程上限 |
| `WEBIDE_EXEC_MAX_OUTPUT_KB` | `200` | 输出截断阈值 |
| `WEBIDE_EXEC_MAX_CODE_KB` | `100` | 提交代码体积上限 |
| `WEBIDE_TERMINAL_UNRESTRICTED` | `0` | 设为 1 将关闭命令白名单（不推荐） |
| `WEBIDE_TERMINAL_ALLOWLIST` | 空 | 追加到默认白名单的命令，逗号分隔 |

### AI 配置

统一入口为 `config/ai_config.json`，优先级：**环境变量 > `ai_config.local.json` > `ai_config.json`**。
修改后可通过 `POST /api/ai/reload` 热加载，无需重启。

---

## 安全配置

### 1. 能力边界现状

| 能力 | 状态 |
|---|---|
| 访问令牌鉴权（全站） | ✅ 已实现 |
| 路径白名单（拒绝绝对路径与越界） | ✅ 已实现 |
| 命令白名单 + shell 元字符过滤 | ✅ 已实现 |
| 资源限制（超时/内存/进程数/输出/代码体积） | ✅ 已实现 |
| 会话级数据隔离 | ✅ 已实现 |
| CORS 收敛到本地前端源 | ✅ 已实现 |
| **容器级隔离** | ❌ **未实现** |

> **关于「危险操作检测」**：旧版本文档曾声称「后端已实现基本的危险操作检测」，
> 该表述与实现不符，已更正。当前实现的是**资源限制**，不是内容审查，
> 也不是安全沙箱 —— 恶意代码仍可读写文件系统与访问网络。

### 2. 生产部署前的必要动作

1. **不要直接暴露到公网**。如确需，必须置于容器或受限用户之下
2. **收敛 CORS**：`backend/app.py` 中的 `ALLOWED_ORIGINS` 改为你的实际域名
3. **限制监听地址**：保持 `WEBIDE_HOST=127.0.0.1`，由 Nginx 对外
4. **禁用或收紧终端**：确认 `WEBIDE_TERMINAL_UNRESTRICTED` 未被设为 1
5. **密钥管理**：AI 密钥通过 `config/ai_config.local.json` 或环境变量提供，切勿提交
6. **定期轮换令牌**：删除 `backend/.webide_token` 后重启即可重新生成

### 3. 容器化建议

由于代码执行能力无法在应用层完全隔离，推荐用容器兜底：

```dockerfile
# 概念示意
FROM python:3.13-slim
RUN useradd -m -u 1000 webide
WORKDIR /app
COPY . .
RUN pip install uv && cd backend && uv sync
USER webide                       # 非 root 运行
# 建议进一步：只读挂载系统目录、限制 CPU/内存、禁用外网出口
CMD ["uv", "run", "--directory", "backend", "python", "app.py"]
```

---

## 性能与容量

### 前端
- 启用 gzip / brotli 压缩
- 静态资源设置长期缓存（Vite 产物带内容哈希）
- 注意：Monaco Editor 体积较大，首屏构建产物约 3.4 MB（gzip 后约 0.9 MB）

### 后端
- 代码执行与命令执行为子进程模型，单次调用开销较大，不适合高并发
- 工具执行会加载完整 DataFrame 到内存，大文件需评估内存
- 产物文件（`backend/out_file/`）会持续累积，建议定期清理

---

## 监控与日志

- 后端使用标准 `logging`，输出到 stdout
- 未授权访问会记录 warning 日志（含来源 IP 与路径）
- 建议接入日志收集（如 ELK / Loki）

### 建议监控项
- 5000 端口存活
- `/run`、`/terminal/execute` 的平均耗时与超时次数
- `backend/out_file/` 与 `backend/data/` 的磁盘占用
- 未授权访问（401）频次

---

## 常见问题

| 现象 | 原因 | 解法 |
|---|---|---|
| 所有接口 401 | 代理未注入 `X-Auth-Token` | 检查 Nginx `proxy_set_header`；令牌值取自 `backend/.webide_token` |
| 跨域失败 | CORS 未包含实际前端域名 | 修改 `app.py` 的 `ALLOWED_ORIGINS` |
| `ModuleNotFoundError` | 依赖未装或 venv 半装损坏 | `cd backend && uv sync`；若仍报错，检查 `.venv/Lib/site-packages/<包名>` 是否为空目录 |
| 代码执行超时 | 死循环或耗时过长 | 检查代码；或调大 `WEBIDE_EXEC_TIMEOUT` |
| 上传大文件失败（413） | 超过体积上限 | 调大 `WEBIDE_MAX_UPLOAD_MB`，并同步 Nginx `client_max_body_size` |
| 命令被安全策略拒绝 | 不在白名单或含 shell 元字符 | 用白名单内命令；扩展白名单用 `WEBIDE_TERMINAL_ALLOWLIST` |
| AI 报「未配置密钥」 | 未配 key | 在 `config/ai_config.local.json` 填 `api_key` |

---

## 版本更新

1. 备份 `backend/data/`、`backend/out_file/` 与 `config/ai_config.local.json`
2. 拉取最新代码
3. `cd backend && uv sync`（依赖有变动时自动更新）
4. `cd frontend && npm install && npm run build`
5. 重启服务

---

## 附：验证部署是否成功

```bash
TOKEN=$(cat backend/.webide_token)

# 1) 服务存活
curl -H "X-Auth-Token: $TOKEN" http://127.0.0.1:5000/python/version

# 2) 工具注册表加载正常（应返回 6 个阶段）
curl -H "X-Auth-Token: $TOKEN" http://127.0.0.1:5000/api/tools

# 3) 未授权访问应被拒绝（应返回 401）
curl -o /dev/null -w "%{http_code}\n" http://127.0.0.1:5000/api/tools

# 4) 前端可访问
curl -o /dev/null -w "%{http_code}\n" http://localhost/
```

开发相关指引见 [快速实验手册.md](快速实验手册.md)。
