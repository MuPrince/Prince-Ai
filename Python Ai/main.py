import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

load_dotenv()

llm = ChatOpenAI(model="gpt-3.5-turbo", api_key=os.getenv("OPENAI_API_KEY"))

prompt = ChatPromptTemplate.from_messages([
    ("system", "你是一个有用的AI助手。"),
    ("user", "{input}")
])

chain = prompt | llm | StrOutputParser()

def main():
    print("LangChain 项目已启动！")
    print("请输入你的问题（输入 'quit' 退出）:")
    
    while True:
        user_input = input("\n> ")
        
        if user_input.lower() == "quit":
            print("再见！")
            break
        
        response = chain.invoke({"input": user_input})
        print("\n回答:", response)

if __name__ == "__main__":
    main()

