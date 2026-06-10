from fastapi import APIRouter
from starlette.responses import StreamingResponse
from agents.dietitian import graph
from agents.dietitian import chat_dietitian, get_messages_history, clear_messages
from schemas.chat import ChatRequest
from typing import List, Optional
from pydantic import BaseModel


router = APIRouter()


# @router.post("/stream")
# async def chat_endpoint(request: ChatRequest):
#     """
#     流式对话
#      Args:
#         request (ChatRequest): 请求参数
#     """
#     return StreamingResponse(
#         chat_dietitian(request.message, request.image_url, request.thread_id),
#         media_type="text/event-stream"
#     )

class IAgentChat(BaseModel):
    message: str
    thread_id: str
    image_url: Optional[List[str]] = []
    
@router.post("/stream")
async def chat_stream(params: IAgentChat):
    
    # 1. 定义一个异步生成器
    async def event_generator():
        try:
            # 💡 核心修改：将之前的 graph.stream(...) 改为 awaitable 的 graph.astream(...)
            # 使用 async for 实时获取大模型输出的每一个 Token 
            async for chunk in graph.astream(
                {"messages": [("user", params.message)]}, # 根据你 graph 的输入结构调整
                config={"configurable": {"thread_id": params.thread_id}}
            ):
                # 根据你 LangGraph 的返回结构提取文本
                # 如果是直接返回大模型流：yield chunk.content
                # 如果是 LangGraph 的节点输出，通常需要按节点名提取：
                if "agent" in chunk:
                    yield chunk["agent"]["messages"][-1].content
                    
        except Exception as e:
            yield f" 流式传输发生错误: {str(e)}"

    # 2. 使用 StreamingResponse 将异步生成器返回给前端
    return StreamingResponse(event_generator(), media_type="text/event-stream")


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
