from langchain_tavily import TavilySearch
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langgraph.checkpoint.sqlite import SqliteSaver
import sqlite3

import os



from dotenv import load_dotenv
load_dotenv()

web_search = TavilySearch(
    max_results=5,
    topic="general"
)


# 4.初始化checkpointer
# 连接sqlite
connection = sqlite3.connect("../db/personal_chief.db", check_same_thread=False)
# 初始化checkpointer
checkpointer = SqliteSaver(connection)
# 自动建表
checkpointer.setup()


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
你是一名私人厨师。收到用户提供的食材照片或清单后，请按照以下流程操作：
1.识别和评估食材：若用户提供照片，首先识别可见食材。基于食材的外观状态，评估其新鲜程度与可用量，整理一份“当前可用食材清单”。
2.智能食谱检索：优先调用web_search工具，以“可用食材清单”为核心关键词，查找可行菜谱。
3.多维度评估与排序：从营养价值和制作难度两个维度对检索到的候选食谱进行量化打分，并根据得分排序，制作简单且营养丰富的排名考前。
"""

agent = create_agent(
    model=llm,
    tools=[web_search],
    system_prompt=system_prompt,
    checkpointer=checkpointer
)