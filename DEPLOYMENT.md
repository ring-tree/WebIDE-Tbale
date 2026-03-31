# WebIDE 部署指南

本指南详细说明如何在生产环境中部署WebIDE项目。

## 目录结构

```
WebIDE-Tbale/
├── frontend/          # 前端Vue项目
├── backend/           # 后端Flask项目
├── dist/              # 前端构建输出目录（构建后生成）
├── files/             # 代码文件存储目录（运行时生成）
├── package.json       # 项目配置和脚本
├── requirements.txt   # Python依赖
└── start_both.bat     # 启动脚本
```

## 环境要求

### 前端
- Node.js 16.0+ 
- npm 7.0+ 或 yarn

### 后端
- Python 3.8+ 
- pip 20.0+

## 部署步骤

### 1. 克隆项目

```bash
git clone <项目仓库地址>
cd WebIDE-Tbale
```

### 2. 安装依赖

#### 前端依赖

```bash
npm install
```

#### 后端依赖

```bash
pip install -r requirements.txt
```

### 3. 构建前端

```bash
npm run build
```

这将在 `frontend/dist` 目录生成构建后的前端文件。

### 4. 配置生产环境

#### 前端配置

在 `frontend/vite.config.js` 中，确保代理配置指向正确的后端地址：

```javascript
proxy: {
  '/run': {
    target: 'http://your-backend-server:5000', // 替换为实际的后端服务器地址
    changeOrigin: true
  },
  // 其他代理配置...
}
```

#### 后端配置

在 `backend/app.py` 中，建议进行以下配置：

1. 禁用调试模式
2. 配置适当的CORS设置
3. 设置合适的超时时间

### 5. 部署后端

可以使用多种方式部署Flask应用：

#### 使用 Gunicorn（推荐）

```bash
# 安装Gunicorn
pip install gunicorn

# 启动应用
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

#### 使用 uWSGI

```bash
# 安装uWSGI
pip install uwsgi

# 启动应用
uwsgi --http 0.0.0.0:5000 --wsgi-file app.py --callable app --processes 4 --threads 2
```

### 6. 配置静态文件服务

前端构建后的文件需要通过Web服务器提供静态文件服务。可以使用以下方式：

#### Nginx 配置示例

```nginx
server {
    listen 80;
    server_name your-domain.com;

    # 静态文件服务
    location / {
        root /path/to/WebIDE-Tbale/frontend/dist;
        index index.html;
        try_files $uri $uri/ /index.html;
    }

    # API代理
    location /run {
        proxy_pass http://localhost:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    location /update {
        proxy_pass http://localhost:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    location /save {
        proxy_pass http://localhost:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    location /load {
        proxy_pass http://localhost:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    location /files {
        proxy_pass http://localhost:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

### 7. 启动服务

#### 开发环境

```bash
# 同时启动前端和后端
npm run dev-all

# 或分别启动
npm run dev      # 前端
npm run server   # 后端
```

#### 生产环境

1. 启动后端服务（使用Gunicorn或uWSGI）
2. 启动Nginx或其他Web服务器提供静态文件服务

## 安全配置

### 1. 代码执行安全

- 后端已实现基本的危险操作检测
- 建议在生产环境中使用更严格的沙箱机制
- 考虑使用Docker容器隔离执行环境

### 2. CORS配置

- 生产环境中应指定具体的域名，而不是使用通配符
- 示例：
  ```python
  header['Access-Control-Allow-Origin'] = 'https://your-domain.com'
  ```

### 3. 文件系统安全

- 限制文件操作的目录范围
- 避免在web根目录下存储用户文件
- 定期清理临时文件

## 性能优化

### 1. 前端优化

- 启用gzip压缩
- 使用CDN加速静态资源
- 配置浏览器缓存

### 2. 后端优化

- 使用缓存减少重复计算
- 优化数据库查询（如果使用数据库）
- 考虑使用异步处理耗时操作

## 监控和日志

### 1. 日志配置

- 后端已配置基本日志记录
- 建议使用专业的日志管理工具，如ELK Stack

### 2. 监控

- 监控服务器资源使用情况
- 监控API响应时间
- 设置错误警报

## 常见问题

### 1. 跨域请求失败

- 检查CORS配置
- 确保前端请求URL正确
- 检查网络连接

### 2. 代码执行超时

- 检查代码是否有死循环
- 调整后端超时设置

### 3. 文件保存失败

- 检查文件权限
- 确保磁盘空间充足
- 检查后端日志获取详细错误信息

## 维护建议

- 定期更新依赖包
- 备份用户文件
- 监控系统性能
- 定期安全检查

## 版本更新

当更新项目时，建议按照以下步骤：

1. 备份现有文件
2. 拉取最新代码
3. 安装新依赖
4. 重新构建前端
5. 重启服务

---

希望本指南能帮助你成功部署WebIDE项目。如有任何问题，请参考项目文档或联系开发团队。