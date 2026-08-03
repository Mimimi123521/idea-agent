# 灵感管家 (Idea Butler)

> 随时随地记录灵感，Agent 自动归类分析，帮你管理工作与生活的待办事项

🔗 **在线体验**: 部署完成后通过手机浏览器访问即可

## 功能特性

- **📝 灵感记录** — 随时输入想法，Agent 自动识别为工作或生活灵感
- **🔍 搜索增强** — 集成 AnySearch，自动搜索背景信息
- **📂 自动归类** — 25 个标签覆盖工作（H2-ICE 技术/管理）和生活（健康/家庭/学习等）
- **📊 智能分析** — 工作类四维评分（可行性/优先级/紧迫性/风险性），生活类简化决策
- **✅ 待办管理** — 自动生成工作待办和生活待办清单
- **📱 PWA 支持** — 可添加到手机桌面，像原生 App 一样使用
- **🌙 离线可用** — 已缓存页面和服务资源

## 快速启动

### 本地运行

```bash
cd idea-agent
pip install -r requirements.txt
python app.py
```

访问 http://localhost:5000

### 生产运行

```bash
gunicorn --bind 0.0.0.0:5000 --workers 2 --timeout 120 app:app
```

## 云端部署（手机访问）

### 方式一：Railway（推荐，免费）

1. 注册 [Railway](https://railway.app/)
2. 点击 **New Project** → **Deploy from GitHub repo**
3. 选择本仓库，Railway 会自动检测 Python 环境
4. 设置启动命令：`gunicorn --bind 0.0.0.0:$PORT --workers 2 --timeout 120 app:app`
5. 部署完成后，Railway 会生成一个公网 URL（如 `https://idea-agent.up.railway.app`）
6. 用手机浏览器打开该 URL，添加到桌面即可

### 方式二：Render

1. 注册 [Render](https://render.com/)
2. 点击 **New +** → **Web Service**
3. 连接 GitHub 仓库
4. Render 会自动识别 `render.yaml`
5. 部署完成后获得公网 URL

### 方式三：Hugging Face Spaces

1. 注册 [Hugging Face](https://huggingface.co/)
2. 创建新 Space，选择 **Docker** 环境
3. 上传本项目的文件
4. Space 会自动构建并部署

## 项目结构

```
idea-agent/
├── app.py                  # Flask 主应用（API 路由）
├── agent_engine.py         # Agent 核心引擎（归类/分析/决策）
├── database.py             # SQLite 数据库操作
├── search_engine.py        # AnySearch 搜索集成
├── requirements.txt        # Python 依赖
├── Dockerfile              # Docker 构建配置
├── render.yaml             # Render 部署配置
├── Procfile                # 启动配置
├── templates/
│   └── index.html          # 移动端 PWA 前端界面
└── static/
    ├── manifest.json       # PWA 配置清单
    ├── sw.js               # Service Worker
    └── icons/              # 应用图标
```

## API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/ideas` | 获取灵感列表（支持筛选） |
| POST | `/api/ideas` | 创建灵感（自动触发分析） |
| GET | `/api/ideas/:id` | 获取灵感详情 |
| PUT | `/api/ideas/:id` | 更新灵感 |
| DELETE | `/api/ideas/:id` | 删除灵感 |
| POST | `/api/ideas/:id/analyze` | 重新分析灵感 |
| POST | `/api/ideas/:id/search` | 为灵感搜索背景信息 |
| POST | `/api/search` | 通用搜索 |
| GET | `/api/stats` | 统计信息 |

## 技术栈

- **后端**: Python Flask + SQLite
- **前端**: 原生 HTML/CSS/JS（无框架依赖）
- **搜索**: AnySearch API
- **部署**: Docker / Gunicorn
- **PWA**: Service Worker + Manifest