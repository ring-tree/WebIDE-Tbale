# WebIDE-Tbale

> 一个面向数据分析场景的浏览器端 IDE：在网页里编辑并运行 Python 代码，同时内置一套覆盖「数据概览 → 清洗 → 特征工程 → 探索性分析 → 建模 → 评估」全流程的可视化工具箱。

WebIDE-Tbale 把「写代码」和「点工具」两种工作方式放进同一个界面：左边是文件树与代码大纲，中间是 Monaco 编辑器（或数据工具箱），底部是终端，右侧是 AI 助手。数据分析工具无需写代码，上传表格、选工具、填参数即可得到图表或结果文件。

---

## 功能特性

### 编辑器与开发体验
- **Monaco 编辑器**：语法高亮、Tab 键智能接管、基于 `jedi` 的 Python 代码补全（带防抖与结果缓存）
- **代码大纲**：正则解析 Python / JavaScript 结构，点击跳转
- **文件树**：浏览、新建、重命名、删除；`project/toolBox` 设为只读保护区
- **终端**：内置命令面板，支持白名单内的系统命令与本地模拟命令
- **AI 助手**：多轮对话，辅助答疑、生成代码、排查报错

### 数据分析工具箱（6 阶段 / 28 个工具）
| 阶段 | 包含工具 |
|---|---|
| 数据概览与诊断 | 数据维度、样本预览、字段信息、缺失值统计、描述性统计 |
| 数据清洗与打磨 | 缺失值填充、去重、重命名、删除列、异常值检测 |
| 特征工程与变换 | Z-Score 标准化、Min-Max 归一化、类别编码、特征选择、训练测试集划分 |
| 探索性分析与可视化 | 直方图、箱线图、散点图、相关性热力图、Cronbach's α 信度 |
| 智能建模 | 线性回归、逻辑回归、决策树、随机森林、K-Means 聚类 |
| 模型评估与验证 | 混淆矩阵、分类评估报告、回归评估指标 |

工具在网页端以表单呈现：参数按类型（数值 / 下拉 / 多选列 / 列名映射）自动渲染，结果以图片、表格或文件形式就地展示。

**多步流程可串联**：变换类工具产出的表格结果，可一键「设为此会话数据集」，直接作为下一步分析的输入——清洗 → 特征工程 → 建模 全流程无需手工导出再导入。

### 工程与安全
- **环境自包含**：后端由 `uv` 管理，前端依赖锁定；不依赖任何全局 Python / Node 安装
- **访问令牌鉴权**：后端全局校验 `X-Auth-Token`，令牌由前端开发代理在服务端注入，浏览器端不持有
- **路径安全**：所有文件操作经统一解析层，拒绝绝对路径与越界访问
- **执行限制**：超时终止进程树、内存与并发进程上限、输出与代码体积截断
- **命令白名单**：终端命令默认受白名单与 shell 元字符过滤保护
- **会话隔离**：数据集与分析产物均按会话分目录存放，互不覆盖、互不可见

---

## 技术栈

| 层 | 技术 |
|---|---|
| 前端 | Vue 3（`<script setup>` SFC）、Vite 5、Monaco Editor |
| 后端 | Python 3.13、Flask 3、flask-cors |
| 数据分析 | pandas、NumPy、Matplotlib、scikit-learn、Seaborn |
| 代码补全 | jedi |
| 环境管理 | uv（Python）、npm（Node） |

---

## 快速开始

### 前置条件
- Python 3.13
- [uv](https://docs.astral.sh/uv/)
- Node.js 18+（项目自带便携版位于 `node_env/`）

### 安装

```bash
git clone <repo-url>
cd WebIDE-Tbale

# 后端依赖（自动创建 backend/.venv）
cd backend && uv sync && cd ..

# 前端依赖
cd frontend && npm install && cd ..
```

### 启动

```bash
# 同时启动前后端
npm run dev-all

# 或分别启动
npm run server   # 后端 → http://127.0.0.1:5000
npm run dev      # 前端 → http://localhost:5173
```

打开 `http://localhost:5173` 即可使用。

> Windows 用户也可直接双击 `start_both.bat`。

更详细的开发指引、目录说明与排错方法见 **[快速实验手册.md](快速实验手册.md)**。

---

## 配置

### AI 配置（统一入口）

所有 AI 相关配置集中在 **`config/ai_config.json`**，业务代码不硬编码任何模型名或密钥：

```json
{
  "enabled": true,
  "default_model": "qwen-plus",
  "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
  "api_key": "",
  "generation": { "temperature": 0.7, "max_tokens": 2048 }
}
```

**更换密钥或模型时，只需修改这一个文件**（无需改动代码，也无需重新构建）。

为避免密钥被提交，推荐把真实密钥写在 `config/ai_config.local.json`（已在 `.gitignore` 中）：

```bash
cp config/ai_config.local.example.json config/ai_config.local.json
# 然后填入真实 api_key
```

配置优先级：**环境变量 > `ai_config.local.json` > `ai_config.json`**。

修改后可通过 `POST /api/ai/reload` 热加载，无需重启服务。

### 环境变量

参见 [.env.example](.env.example)，涵盖服务绑定、执行限制、上传上限与命令白名单等。

### 访问令牌

后端首次启动会自动生成令牌并写入 `backend/.webide_token`（已 gitignore）。
前端开发服务器读取该文件并在代理层注入请求头，因此**浏览器端不持有令牌**，直接访问 5000 端口会被拒绝。

---

## 项目结构

```
WebIDE-Tbale/
├── frontend/                    # Vue 3 + Vite 单页应用
│   ├── src/
│   │   ├── App.vue              # 主布局与全局状态
│   │   ├── components/
│   │   │   ├── MonacoEditor.vue # 编辑器 + 补全
│   │   │   ├── FileTree.vue     # 文件树
│   │   │   ├── TreeNode.vue     # 树节点
│   │   │   ├── OutlineView.vue  # 代码大纲
│   │   │   ├── Terminal.vue     # 终端
│   │   │   ├── AiChat.vue       # AI 对话
│   │   │   └── ToolPanel.vue    # 数据分析工具箱
│   │   └── utils/api.js         # 会话标识与请求封装
│   └── vite.config.js           # 开发代理（注入令牌）
├── backend/                     # Flask 服务
│   ├── app.py                   # 全部路由
│   ├── pyproject.toml           # 依赖权威声明
│   ├── toolBox/                 # 工具注册表
│   └── tests/                   # pytest 回归测试
├── config/                      # 全局 AI 配置
│   └── ai_config.json
├── project/                     # IDE 工作区（被编辑的目标目录）
│   └── toolBox/system_tool/     # 28 个分析工具的实现
├── env_config.py                # 运行时路径解析
└── package.json                 # 根级编排脚本
```

---

## API 概览

| 分组 | 端点 | 说明 |
|---|---|---|
| 代码 | `POST /run`、`POST /update` | 执行代码、获取补全 |
| 文件 | `GET /api/files`、`POST /api/files/{create,delete,rename}`、`POST /load`、`POST /save` | 文件树与读写 |
| 终端 | `POST /terminal/execute` | 白名单命令执行 |
| 数据 | `POST /api/upload`、`GET /api/data/info`、`POST /api/data/adopt` | 上传数据集、读取结构、把分析产物设回数据集 |
| 工具箱 | `GET /api/tools`、`GET /api/tools/all`、`GET /api/tools/search`、`POST /api/tools/<name>` | 工具发现与执行 |
| 产物 | `GET /api/output/<session>/<file>` | 访问生成的图表 / CSV（按会话隔离） |
| AI | `POST /api/ai/chat`、`GET /api/ai/models`、`GET /api/ai/config`、`POST /api/ai/reload` | 对话与配置 |
| 环境 | `GET /python/version` | 解释器版本 |

工具执行支持两种参数写法，二者等价：

```jsonc
// A) 简化写法
{ "column": "age", "bins": 10 }

// B) 完整写法
{ "methodConfig": { "column": "age", "bins": 10 } }
```

---

## 测试

```bash
cd backend
uv run pytest
```

共 **115 项**用例，覆盖五个层面：

| 层面 | 内容 |
|---|---|
| 安全 | 鉴权、路径越界、只读保护、错误信息脱敏 |
| 执行 | 超时、内存与进程上限、输出截断、命令白名单 |
| 接口 | 数据集上传与结构、会话隔离、产物访问控制 |
| 工具箱-数值 | 整型列兼容性、缺失值保留、常量列跳过 |
| 工具箱-建模 | 逻辑回归（二/多分类）、树模型、聚类、评估指标 |

---

## 安全须知

本项目**允许执行代码与系统命令**，这是它的核心能力，也是它的主要风险：

- 默认仅监听 `127.0.0.1`，请勿在不可信网络中暴露；确需跨机访问时设置 `WEBIDE_HOST` 并自行评估风险
- 已实现的能力边界：令牌鉴权、路径白名单、命令白名单、资源限制
- **未实现**：容器级隔离。当前限制属于「资源限制」而非「安全沙箱」，恶意代码仍可读写文件系统与访问网络。生产环境请置于容器或受限用户之下
- 请勿把真实密钥提交到仓库；`config/ai_config.json` 中的 `api_key` 应保持为空

---

## 已知限制

- `/run` 与 `/terminal/execute` 缺少容器级隔离（见上）
- 代码执行与命令执行为子进程模型，单次调用开销较大，不适合高并发
- 前端未做移动端适配

---

## 许可证

见 [LICENSE](LICENSE)。
