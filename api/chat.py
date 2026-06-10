from fastapi import APIRouter
from starlette.responses import StreamingResponse

from agents.dietitian import chat_dietitian, get_messages_history, clear_messages
from schemas.chat import ChatRequest

router = APIRouter()


@router.post("/stream")
async def chat_endpoint(request: ChatRequest):
    """
    流式对话
     Args:
        request (ChatRequest): 请求参数
    """
    return StreamingResponse(
        chat_dietitian(request.message, request.image_url, request.thread_id),
        media_type="text/event-stream"
    )



@router.get("/history/{thread_id}")
async def get_chat_history(thread_id: str):
    """
    获取历史消息
     Args:
        thread_id (str): 会话id
    """
    messages = get_messages_history(thread_id)
    return {"messages": messages}


@router.delete("/history/{thread_id}")
async def clear_chat_history(thread_id: str):
    """
    清空历史消息
    Args:
        thread_id (str): 会话id
    """
    clear_messages(thread_id)
    return {"success": True}
