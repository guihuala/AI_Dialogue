from openai import OpenAI
import os
from typing import List, Dict, Optional

class LLMService:
    def __init__(self, api_key: Optional[str] = None, model: str = "deepseek-chat"):
        # 1. 读取 API Key
        # 修正：优先读取 .env 里的 DEEPSEEK_API_KEY
        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY")
        
        if not self.api_key:
            print("⚠️ 警告: 未找到 DEEPSEEK_API_KEY，API 调用将失败。请检查 .env 文件。")
            self.api_key = "dummy"

        # 2. 初始化 OpenAI 客户端 (DeepSeek 兼容)
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

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Context:\n{context}\n\nUser: {user_input}"}
        ]

        try:
            # 这里的 self.model 必须在 __init__ 里定义过
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
            )
            return completion.choices[0].message.content
        except Exception as e:
            print(f"LLM Error Details: {e}") # 在后端打印详细错误
            return f"Error calling LLM: {str(e)}"
        if not self.api_key or self.api_key == "dummy":
            return "Error: API Key not set."

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Context:\n{context}\n\nUser: {user_input}"}
        ]

        try:
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
            )
            return completion.choices[0].message.content
        except Exception as e:
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