# ========== 后端 Dockerfile ==========
# 智能任务规划系统 - FastAPI 后端
# 使用多阶段构建减小镜像体积
#

# ---------- 阶段1: 构建依赖 ----------
FROM python:3.11-slim AS builder

WORKDIR /app

# 安装编译工具（部分包可能无预编译 wheel，需从源码构建）
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        gcc \
        g++ \
        libffi-dev \
        libssl-dev \
        libfreetype6-dev \
        libpng-dev \
        pkg-config \
    && rm -rf /var/lib/apt/lists/*

# 先复制依赖文件，利用 Docker 缓存层（依赖不常变）
COPY requirements.txt .

# 安装 Python 依赖到用户目录
RUN pip install --no-cache-dir --user -r requirements.txt

# ---------- 阶段2: 运行镜像 ----------
FROM python:3.11-slim

WORKDIR /app

# 安装运行时系统库（matplotlib、cryptography 等需要）
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libfreetype6 \
        libpng16-16 \
        libssl3 \
        libffi8 \
    && rm -rf /var/lib/apt/lists/*

# 从构建阶段复制已安装的 Python 包
COPY --from=builder /root/.local /root/.local

# 确保 pip 安装的脚本在 PATH 中
ENV PATH=/root/.local/bin:$PATH

# 复制后端源码
COPY . .

# 创建数据和日志目录
RUN mkdir -p /app/data /app/logs

# 暴露端口
EXPOSE 8080

# 健康检查
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/')" || exit 1

# 启动命令
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
