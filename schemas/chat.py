from typing import List

from pydantic import BaseModel

# ---  数据模型 ---
class ChatRequest(BaseModel):
    # 消息内容
    message: str
    # 图片地址
    image_url: List[str]
    # 会话id
    thread_id: str