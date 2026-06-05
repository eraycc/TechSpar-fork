# 阶段1: 构建前端
FROM node:22-alpine AS frontend-builder

WORKDIR /app/frontend

# 复制前端依赖文件
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci --only=production && npm cache clean --force

# 复制前端源码并构建
COPY frontend/ .
RUN npm run build

# 阶段2: 构建后端环境
FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖（包括 nginx）
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        gcc \
        python3-dev \
        nginx \
        supervisor \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --upgrade pip

# 复制后端依赖并安装
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制后端代码
COPY backend/ backend/

# 复制前端构建产物到 nginx 目录
COPY --from=frontend-builder /app/frontend/dist /usr/share/nginx/html

# 复制前端 nginx 配置
COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf

# 配置 supervisor 同时运行后端和 nginx
RUN echo '[supervisord]\nnodaemon=true\n\n[program:backend]\ncommand=uvicorn backend.main:app --host 0.0.0.0 --port 8000\ndirectory=/app\nautostart=true\nautorestart=true\nstdout_logfile=/dev/stdout\nstdout_logfile_maxbytes=0\nstderr_logfile=/dev/stderr\nstderr_logfile_maxbytes=0\n\n[program:nginx]\ncommand=nginx -g "daemon off;"\nautostart=true\nautorestart=true\nstdout_logfile=/dev/stdout\nstdout_logfile_maxbytes=0\nstderr_logfile=/dev/stderr\nstderr_logfile_maxbytes=0' > /etc/supervisor/conf.d/app.conf

# 暴露端口（nginx 端口）
EXPOSE 80

# 启动 supervisor
CMD ["supervisord", "-n", "-c", "/etc/supervisor/supervisord.conf"]
