import os
from langchain_openai import ChatOpenAI
from typing import AsyncGenerator
import asyncio
import json

def create_llm():
    api_key = os.getenv("DASHSCOPE_API_KEY")
    if not api_key:
        raise ValueError("请在 .env 文件中设置 DASHSCOPE_API_KEY")
    
    return ChatOpenAI(
        model="qwen-turbo",
        api_key=api_key,
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
    )

llm = create_llm()

system_prompt = """
你是一名图形设计师
你需要根据用户的描述生成对应的图片。
用户问题：
{query}
"""

def agent(query: str):
    """原有的 agent 函数保持不变"""
    print(query)
    response = llm.invoke(system_prompt.format(query=query))
    return response.content
    # return system_prompt.format(query=query)



async def stream_response(query: str) -> AsyncGenerator[str, None]:
    """流式生成响应"""
    try:
        # 方式1：如果 llm 支持流式调用
        # 检查你的 llm 对象是否支持 stream 参数
        # if hasattr(llm, 'stream') or (hasattr(llm, 'invoke') and 'stream' in llm.__class__.__name__.lower()):
        #     # 使用流式 API
        #     async for chunk in llm.astream(system_prompt.format(query=query)):
        #         # 假设 chunk 有 content 属性
        #         content = chunk.content if hasattr(chunk, 'content') else str(chunk)
        #         yield f"data: {json.dumps({'content': content, 'status': 'streaming'}, ensure_ascii=False)}\n\n"
        #         await asyncio.sleep(0.01)  # 可选：控制输出速度
        # else:
        #     # 方式2：如果不支持流式，先获取完整响应再模拟流式输出
        #     response = agent(query)
        #     # 逐字符输出，模拟流式效果
        #     for char in response:
        #         yield f"data: {json.dumps({'content': char, 'status': 'streaming'}, ensure_ascii=False)}\n\n"
        #         await asyncio.sleep(0.02)  # 模拟打字效果
        # 方式2：如果不支持流式，先获取完整响应再模拟流式输出
        response = agent(query)
        # 逐字符输出，模拟流式效果
        for char in response:
            yield f"data: {json.dumps({'content': char, 'status': 'streaming'}, ensure_ascii=False)}\n\n"
            await asyncio.sleep(0.02)  # 模拟打字效果
        # 发送完成信号
        yield f"data: {json.dumps({'status': 'completed'}, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"
        
    except Exception as e:
        # 错误处理
        error_msg = json.dumps({'error': str(e), 'status': 'error'}, ensure_ascii=False)
        yield f"data: {error_msg}\n\n"
