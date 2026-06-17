# 🐳 智能任务规划系统 - Docker 部署指南

## 📁 项目结构

```
demo_plan/
├── backend/                 # FastAPI 后端
│   ├── Dockerfile           # 后端镜像
│   ├── .dockerignore
│   └── requirements.txt
├── frontend/                # Vue 3 前端
│   ├── Dockerfile           # 前端镜像（多阶段构建）
│   ├── .dockerignore
│   └── nginx.conf           # Nginx 配置
├── docker-compose.yml       # 完整版编排（MySQL + Redis）
├── docker-compose.lite.yml  # 轻量版编排（SQLite）
├── .env.docker              # 环境变量模板
└── README_DOCKER.md         # 本文档
```

## 🚀 快速开始

### 前置要求

- 安装 [Docker](https://www.docker.com/products/docker-desktop/)（20.10+）
- 安装 [Docker Compose](https://docs.docker.com/compose/install/)（2.0+）
- 获取 [DeepSeek API Key](https://platform.deepseek.com/)（免费注册）

### 方式一：轻量版（推荐给朋友体验）

> 使用 SQLite 数据库，无需 MySQL/Redis，启动最简单。

```bash
# 1. 进入项目目录
cd demo_plan

# 2. 配置环境变量
cp .env.docker .env
# 编辑 .env，填入你的 DEEPSEEK_API_KEY 和 WEATHER_API_KEY

# 3. 构建并启动
docker compose -f docker-compose.lite.yml up -d

# 4. 访问应用
# 打开浏览器 → http://localhost
```

### 方式二：完整版（MySQL + Redis）

> 适合长期使用，性能更好。

```bash
# 1. 进入项目目录
cd demo_plan

# 2. 配置环境变量
cp .env.docker .env
# 编辑 .env，填入：
#   - DEEPSEEK_API_KEY（必填）
#   - WEATHER_API_KEY（必填）
#   - MYSQL_ROOT_PASSWORD（可选，默认 demo_plan_2024）

# 3. 构建并启动所有服务
docker compose up -d

# 4. 查看启动状态
docker compose ps

# 5. 查看日志（如有问题）
docker compose logs -f backend

# 6. 访问应用
# 打开浏览器 → http://localhost
```

## 📋 常用命令

```bash
# ---- 启动 ----
docker compose up -d                          # 完整版启动
docker compose -f docker-compose.lite.yml up -d  # 轻量版启动

# ---- 停止 ----
docker compose down                           # 停止并删除容器
docker compose down -v                        # 同时删除数据卷（⚠️ 数据会丢失）

# ---- 查看 ----
docker compose ps                             # 查看容器状态
docker compose logs -f backend                # 实时查看后端日志
docker compose logs -f frontend               # 实时查看前端日志

# ---- 更新 ----
docker compose build --no-cache               # 重新构建镜像
docker compose up -d --force-recreate         # 重建并重启容器
```

## 🌐 端口说明

| 服务 | 容器端口 | 映射端口（可修改） |
|------|---------|------------------|
| 前端（Nginx） | 80 | `FRONTEND_PORT`（默认 80） |
| 后端（FastAPI） | 8080 | `BACKEND_PORT`（默认 8080） |
| MySQL | 3306 | `MYSQL_PORT`（默认 3307） |
| Redis | 6379 | `REDIS_PORT`（默认 6380） |

> 修改端口：编辑 `.env` 文件中的对应变量，然后重启。

## 👥 分享给朋友的三种方式

### 方式 A：发送项目文件（推荐）

```bash
# 1. 把整个项目文件夹（含 Docker 配置）打包
#    删除 .env 中的真实密钥后再发送！

# 2. 朋友收到后执行：
cd demo_plan
cp .env.docker .env
# 编辑 .env 填入自己的 API Key
docker compose -f docker-compose.lite.yml up -d
# 打开浏览器 → http://localhost
```

### 方式 B：导出镜像文件

```bash
# 1. 你在本地构建并导出镜像
docker compose build
docker save -o plan-backend.tar demo_plan-backend:latest
docker save -o plan-frontend.tar demo_plan-frontend:latest

# 2. 把 .tar 文件和 docker-compose.yml 发给朋友
# 3. 朋友导入镜像
docker load -i plan-backend.tar
docker load -i plan-frontend.tar
docker compose -f docker-compose.lite.yml up -d
```

### 方式 C：上传到 Docker Hub

```bash
# 1. 登录 Docker Hub（先注册 https://hub.docker.com）
docker login

# 2. 给镜像打标签（替换 yourname 为你的用户名）
docker tag demo_plan-backend YOUR_DOCKER_USERNAME/task-planner-backend:latest
docker tag demo_plan-frontend YOUR_DOCKER_USERNAME/task-planner-frontend:latest

# 3. 推送
docker push YOUR_DOCKER_USERNAME/task-planner-backend:latest
docker push YOUR_DOCKER_USERNAME/task-planner-frontend:latest

# 4. 朋友拉取运行
docker pull YOUR_DOCKER_USERNAME/task-planner-backend:latest
docker pull YOUR_DOCKER_USERNAME/task-planner-frontend:latest
# 然后用自定义的 docker-compose.yml 启动
```

## 🔧 配置说明

### 必需配置

| 变量 | 说明 | 获取地址 |
|------|------|---------|
| `DEEPSEEK_API_KEY` | DeepSeek AI 接口密钥 | https://platform.deepseek.com/ |
| `WEATHER_API_KEY` | 天气数据接口密钥 | https://www.qweather.com/ |

### 可选配置（完整版）

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `MYSQL_ROOT_PASSWORD` | `demo_plan_2024` | MySQL root 密码 |
| `MYSQL_DATABASE` | `task_planner` | 数据库名 |
| `FRONTEND_PORT` | `80` | 前端访问端口 |
| `BACKEND_PORT` | `8080` | 后端 API 端口 |

## ❓ 常见问题

### Q: 启动后页面空白？

检查后端是否正常：访问 http://localhost:8080/ 应返回 JSON。

```bash
docker compose logs backend
```

### Q: 提示端口被占用？

修改 `.env` 中的端口映射：
```
FRONTEND_PORT=8081
BACKEND_PORT=8082
```

### Q: API 调用失败？

确认 `.env` 中填入了正确的 `DEEPSEEK_API_KEY`。

### Q: 轻量版和完整版怎么选？

- **轻量版**：SQLite + 无 Redis，适合演示和体验，数据量不大时性能足够
- **完整版**：MySQL + Redis，适合长期使用，支持缓存和异步任务队列

### Q: 如何重置数据库？

```bash
# 轻量版
docker compose -f docker-compose.lite.yml down -v
docker compose -f docker-compose.lite.yml up -d

# 完整版
docker compose down -v
docker compose up -d
```
