
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api import chat, file
from common.logger import setup_logging

from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

# 初始化日志配置
setup_logging()

app = FastAPI(
    title="Personal Chief API",
    description="私厨",
    version="0.1.0"
)

# ==================================================================
# 1. 后端 API 接口路由挂载 (严格对接前端 baseURL: '/dietitian/api')
# ==================================================================
# 确保前缀完全一致，这样前端请求 /dietitian/api/chat/... 时才能正确匹配
app.include_router(chat.router, prefix="/dietitian/api/chat")
app.include_router(file.router, prefix="/dietitian/api/file")

# ==================================================================
# 2. 前端静态资源托管 (必须放在所有 API 路由的下方)
# ==================================================================

# 获取当前 main.py 所在目录的绝对路径
current_dir = os.path.dirname(os.path.abspath(__file__))
static_dir = os.path.join(current_dir, "static")

# 直接挂载 assets 目录。
# 移除 if 判断，如果路径不存在，FastAPI 启动时会直接在控制台报错，更方便你排查 static 文件夹有没有放对地方。
app.mount("/assets", StaticFiles(directory=os.path.join(static_dir, "assets")), name="assets")


# 3. 兜底路由：处理首页、图标以及 Vue 路由刷新问题
@app.get("/{catchall:path}")
async def serve_frontend(catchall: str):
    # 检查是否请求的是 static 目录下的具体文件（如 /favicon.svg, /icons.svg）
    file_path = os.path.join(static_dir, catchall)
    if os.path.exists(file_path) and os.path.isfile(file_path):
        return FileResponse(file_path)

    # 其他所有情况（如刷新页面、访问不存在的路由），一律返回 index.html
    return FileResponse(os.path.join(static_dir, "index.html"))

# # 1. 配置跨域资源共享 (CORS)
# # 插件开发中，由于请求来自浏览器扩展环境，必须正确配置 CORS
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],  # 生产环境建议指定插件的 ID 或具体域名
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# # 2.挂载路由
# app.include_router(chat.router, prefix="/dietitian/api", tags=["对话"])
# app.include_router(file.router, prefix="/dietitian/api", tags=["申请上传签名url"])


if __name__ == "__main__":
    import uvicorn
    # 启动命令：python -m app.main
    uvicorn.run("main:app", host="127.0.0.1", port=8001, reload=True)