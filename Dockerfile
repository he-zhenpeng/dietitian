# 使用官方轻量版 Python 镜像
FROM python:3.13-slim

# 从 astral 官方镜像中把 uv 工具直接复制过来，加速依赖安装
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# 设置容器内的工作目录
WORKDIR /app

# 强迫 Python 别缓冲输出，方便在 Docker 日志里实时看到 print 和 log
ENV PYTHONUNBUFFERED=1

# 先复制依赖描述文件（利用 Docker 缓存机制，只要依赖没变，下次打包直接跳过安装）
COPY pyproject.toml uv.lock ./

# 使用 uv 进行同步安装，--frozen 确保严格锁定版本，--no-cache 减小镜像体积
RUN uv sync --frozen --no-cache

# 复制整个项目（包含你已经放好的 static 静态网页文件夹）到容器中
COPY . .

# 暴露 main.py 中配置的 8001 端口
EXPOSE 8001

# 启动命令：使用 uv 运行 uvicorn。
# 🚨 注意：这里必须把 host 改为 0.0.0.0，否则容器外无法访问该服务
CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]
