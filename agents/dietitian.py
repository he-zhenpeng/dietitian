from langchain.chat_models import init_chat_model
from langchain.agents import create_agent
from langchain_core.messages import HumanMessage, AIMessage, AIMessageChunk
from langgraph.checkpoint.mongodb import MongoDBSaver
from langchain_tavily import TavilySearch
from pymongo import MongoClient  # 引入原生客户端以彻底移除 with
from typing import List

import os
import dotenv

from common.logger import logger

dotenv.load_dotenv()  # 加载 .env 文件

# 构建聊天模型
model = init_chat_model(
    model=os.getenv("MODEL_NAME"),
    model_provider="openai",
    base_url=os.getenv("OPENAI_API_URL"),
    api_key=os.getenv("OpenAI_API_KEY"),
)

# 工具
web_search = TavilySearch(
    max_results=5,
    topic="general",
    tavily_api_key=os.getenv("TVILY_API_KEY")
)

#  系统提示词
system_prompt = """
# 角色

你是一名 AI 私人营养师（Nutrition Chef）。

你的目标是：
根据用户提供的食材图片或食材清单，生成“健康、营养均衡、制作简单、食材利用率高”的菜谱推荐。

---

# 工作流程（必须严格执行）

## 1. 食材识别与评估

如果用户上传图片：
- 识别所有食材
- 判断新鲜度、可用量、是否变质
- 输出“当前可用食材清单”

格式：

- 食材名｜新鲜度（1~10）｜建议优先级

若发现疑似变质食材，必须提醒用户不要食用。

---

## 2. 营养需求分析

优先结合用户目标：
- 减脂
- 增肌
- 控糖
- 高蛋白
- 低盐
- 儿童餐
- 老人餐

如果用户未说明，默认按“普通成年人均衡饮食”处理。

---

## 3. 智能食谱检索

必须优先调用 web_search 工具 搜索真实菜谱。

搜索关键词需结合：
- 可用食材
- 用户目标
- 菜系
- 难度

例如：
“鸡胸肉 西兰花 减脂 高蛋白 食谱”

只有搜索不到时，才能自行生成菜谱。

---

## 4. 菜谱评分

对候选菜谱进行评分：

- 营养价值（0~10）
- 健康程度（0~10）
- 制作难度（0～ 10 ）越简单分越高
- 食材利用率（0~10）

综合得分：
营养价值35% + 健康程度25% + 制作难度20% + 食材利用率20%

优先推荐：
- 高蛋白
- 高纤维
- 低油低糖
- 制作简单
- 少浪费

---

## 5. 结构化输出

按得分排序输出，要包含食谱信息、得分、推荐理由、营养分析、使用食材、做法、web_search查询出来食谱的参考图片，帮助用户快速做出决策。

# 推荐菜谱示例

## TOP 1：xxx
综合评分：92/100

### 推荐理由
- 高蛋白低脂
- 制作简单
- 食材利用率高
- ...

### 营养分析
- 热量：
- 蛋白质：
- 碳水：
- 脂肪：

### 使用食材
- xxx
- xxx

### 做法
1. ...
2. ...

### 营养建议
- ...

### 参考图
![图片描述](参考图链接)

---

# 规则

你必须：
- 优先食品安全
- 优先营养均衡
- 优先真实可执行
- 优先减少浪费
- 优先调用 web_search 工具 搜索不到了才能自己发挥。

禁止：
- 编造危险饮食建议
- 忽略过敏与变质风险
- 只输出菜名不给做法
"""

# 创建记忆数据库
MONGODB_URI = os.getenv("MONGODB_URI")
checkpointer = MongoDBSaver(MongoClient(MONGODB_URI))

# 创建agent
agent = create_agent(
    model=model,
    tools=[web_search],
    system_prompt=system_prompt,
    checkpointer=checkpointer
)


# 流式对话
async def chat_dietitian(text: str, images: List[str], thread_id: str):
    """
    对话营养师
    :param text: 用户说的话
    :param images: 图片
    :param thread_id:  会话id
    :return:
    """
    logger.info(f"[用户]: {text}, images: {images}, thread_id: {thread_id}")
    try:
        # 判断是否有图片，封装不同格式的消息
        if not images or all(not img.strip() for img in images):
            message = HumanMessage(content=text)
        else:
            # 有多张图片，封装成列表
            content_list = [{"type": "image", "url": url} for url in images if url.strip()]
            # 加上文字
            content_list.append({"type": "text", "text": text})
            message = HumanMessage(content=content_list)

        # 流式调用Agent
        for chunk, metadata in agent.stream(
                {"messages": [message]},
                {"configurable": {"thread_id": thread_id}},
                stream_mode="messages"
        ):
            if isinstance(chunk, AIMessageChunk) and chunk.content:
                yield chunk.content

    except Exception as e:
        logger.error(f"\n[错误]: {str(e)}")
        yield "信息检索失败，试试看手动输入食物列表？"


# 清空会话
def clear_messages(thread_id: str):
    """
    清空会话
    :param thread_id: 会话id
    """
    logger.info(f"清空历史消息，thread_id: {thread_id}")
    checkpointer.delete_thread(thread_id)


# 查询会话历史
def get_messages_history(thread_id: str) -> list[dict[str, str]]:
    """
    获取会话历史
    :param thread_id: 会话id
    :return: 历史记录
    """
    logger.info(f"获取历史消息，thread_id: {thread_id}")

    # 根据 thread_id 查询 checkpoint
    checkpoint = checkpointer.get({"configurable": {"thread_id": thread_id}})

    # 如果不存在，返回空列表
    if not checkpoint:
        return []

    # 安全获取 messages
    channel_values = checkpoint.get("channel_values")
    if not channel_values:
        return []

    messages = channel_values.get("messages", [])
    if not messages:
        return []

    # 转换消息格式
    result = []
    for msg in messages:
        if not msg.content:
            continue
        if isinstance(msg, HumanMessage):
            # 如果 msg.content 是列表（多图+文字）
            if isinstance(msg.content, list):
                texts = []
                images = []
                for item in msg.content:
                    if isinstance(item, dict):
                        if item.get("type") == "image" and item.get("url"):
                            images.append(item["url"])
                        elif item.get("type") == "text" and item.get("text"):
                            texts.append(item["text"])
                result.append({
                    "role": "user",
                    "message": " ".join(texts) if texts else "",
                    "image_url": images
                })
                print(msg.content)
            else:
                # 纯文本消息
                result.append({
                    "role": "user",
                    "message": msg.content,
                    "image_url": []
                })


        elif isinstance(msg, AIMessage):
            result.append({"role": "assistant", "message": msg.content})

    return result
