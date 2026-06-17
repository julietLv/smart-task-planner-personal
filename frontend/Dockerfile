# ========== 前端 Dockerfile ==========
# 智能任务规划系统 - Vue 3 前端
# 多阶段构建：Node 构建 → Nginx 服务

# ---------- 阶段1: 构建 ----------
FROM node:20-alpine AS builder

WORKDIR /app

# 复制依赖文件
COPY package.json package-lock.json ./

# 安装依赖
RUN npm ci

# 复制源码
COPY . .

# 构建生产版本
RUN npm run build

# ---------- 阶段2: 运行（Nginx）----------
FROM nginx:alpine

# 复制构建产物到 Nginx 目录
COPY --from=builder /app/dist /usr/share/nginx/html

# 复制自定义 Nginx 配置
COPY nginx.conf /etc/nginx/conf.d/default.conf

# 暴露端口
EXPOSE 80

# 健康检查
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD wget -qO- http://localhost:80/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
