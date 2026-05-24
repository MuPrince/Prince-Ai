import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

load_dotenv()

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

prompt = ChatPromptTemplate.from_messages([
    ("system", "你是一个有用的AI助手。"),
    ("user", "{input}")
])

chain = prompt | llm | StrOutputParser()

def main():
    print("LangChain 项目已启动！（使用阿里云百炼）")
    print("请输入你的问题（输入 'quit' 退出）:")
    
    while True:
        user_input = input("\n> ")
        
        if user_input.lower() == "quit":
            print("再见！")
            break
        
        try:
            response = chain.invoke({"input": user_input})
            print("\n回答:", response)
        except Exception as e:
            print(f"\n错误: {e}")

if __name__ == "__main__":
    main()
