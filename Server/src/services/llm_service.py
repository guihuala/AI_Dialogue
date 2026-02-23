from openai import OpenAI
import os
from typing import List, Dict, Optional

from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv()) # 自动向上层目录寻找 .env 并加载

class LLMService:
    def __init__(self, api_key: Optional[str] = None, model: str = "deepseek-chat"):
        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY")
        
        if not self.api_key:
            print("⚠️ 警告: 未找到 DEEPSEEK_API_KEY，API 调用将失败。请检查 .env 文件。")
            self.api_key = "dummy"

        # 2. 初始化 OpenAI 客户端
        self.client = OpenAI(
            base_url="https://api.deepseek.com", 
            api_key=self.api_key,
        )
        
        # 3. 修复：确保 self.model 被正确赋值
        self.model = model 

    def set_model(self, model: str):
        self.model = model

    def generate_response(self, system_prompt: str, user_input: str, context: str = "") -> str:
        if self.api_key == "dummy":
            return "Error: API Key is missing. Please check .env file."

        # 构造完整的消息列表
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Context:\n{context}\n\nUser: {user_input}"}
        ]

        print("\n" + "="*40)
        print("🚀 [SENDING TO LLM] (发送给 AI)")
        print("-" * 20)
        print(f"【System Prompt】:\n{system_prompt}")
        print("-" * 20)
        print(f"【User Input + Context】:\n{context}\nUser: {user_input}")
        print("="*40 + "\n")

        try:
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
            )
            content = completion.choices[0].message.content

            print("\n" + "="*40)
            print("🤖 [LLM RESPONSE] (AI 回复)")
            print("-" * 20)
            print(content)
            print("="*40 + "\n")

            return content
        except Exception as e:
            print(f"❌ LLM Error Details: {e}") 
            return f"Error calling LLM: {str(e)}"
            
    def generate_response_stream(self, system_prompt: str, user_input: str, context: str = ""):
        if not self.api_key or self.api_key == "dummy":
            yield "Error: API Key not set."
            return

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Context:\n{context}\n\nUser: {user_input}"}
        ]
        
        try:
            stream = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                stream=True,
            )
            for chunk in stream:
                if chunk.choices[0].delta.content is not None:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            yield f"Error calling LLM: {str(e)}"

    def generate_summary(self, memories: str) -> str:
        if not self.api_key:
            return "Error: API Key not set."
            
        prompt = f"Summarize the following events into a concise memory update:\n{memories}"
        
        try:
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
            )
            return completion.choices[0].message.content
        except Exception as e:
            return f"Error summarizing: {str(e)}"

if __name__=="__main__":
    llm_service = LLMService()
    response = llm_service.generate_response(
        system_prompt="You are a helpful assistant.",
        user_input="Hello, how are you?",
        context="Some relevant context."
    )
    print("Response:", response)