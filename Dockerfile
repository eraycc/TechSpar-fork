# 阶段1: 构建前端
FROM node:22-alpine AS frontend-builder

WORKDIR /app/frontend

# 先复制依赖文件（利用 Docker 缓存）
COPY frontend/package.json frontend/package-lock.json* ./

# 安装所有依赖
RUN npm ci

# 复制源码并构建
COPY frontend/ .
RUN npm run build

# 阶段2: 构建后端
FROM python:3.11-slim AS backend-builder

WORKDIR /app

# 复制后端依赖并安装（利用 Docker 缓存）
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 阶段3: 最终镜像
FROM python:3.11-slim

WORKDIR /app

# 安装运行时依赖（只安装必要的，不包含 gcc 等编译工具）
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        nginx \
        supervisor \
    && rm -rf /var/lib/apt/lists/*

# 从后端构建阶段复制 Python 包
COPY --from=backend-builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=backend-builder /usr/local/bin /usr/local/bin

# 复制后端代码
COPY backend/ backend/

# 从前端构建阶段复制构建产物
COPY --from=frontend-builder /app/frontend/dist /usr/share/nginx/html

# 配置 nginx（如果没有自定义配置）
RUN echo 'server { \
    listen 80; \
    server_name _; \
    location / { \
        root /usr/share/nginx/html; \
        try_files $uri $uri/ /index.html; \
    } \
    location /api { \
        proxy_pass http://localhost:8000; \
        proxy_set_header Host $host; \
        proxy_set_header X-Real-IP $remote_addr; \
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for; \
    } \
}' > /etc/nginx/conf.d/default.conf

# 配置 supervisor
RUN echo '[supervisord]\nnodaemon=true\n\n[program:backend]\ncommand=uvicorn backend.main:app --host 0.0.0.0 --port 8000\ndirectory=/app\nautostart=true\nautorestart=true\n\n[program:nginx]\ncommand=nginx -g "daemon off;"\nautostart=true\nautorestart=true' > /etc/supervisor/conf.d/app.conf

EXPOSE 80

CMD ["supervisord", "-n", "-c", "/etc/supervisor/supervisord.conf"]
