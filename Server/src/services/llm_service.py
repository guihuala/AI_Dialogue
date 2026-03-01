from openai import OpenAI, AsyncOpenAI
import os
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

class LLMService:
    def __init__(self, api_key: Optional[str] = None, base_url: str = "https://api.deepseek.com/v1", model: str = "deepseek-chat"):
        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY") or "dummy"
        self.base_url = base_url
        self.model = model
        
        # 🌟 同步与异步客户端同时初始化
        self.client = OpenAI(base_url=self.base_url, api_key=self.api_key)
        self.async_client = AsyncOpenAI(base_url=self.base_url, api_key=self.api_key)

    def update_config(self, api_key: str, base_url: str, model: str):
        if not api_key:
            api_key = os.getenv("DEEPSEEK_API_KEY") or "dummy"
            
        if api_key != self.api_key or base_url != self.base_url:
            self.api_key = api_key
            self.base_url = base_url
            self.client = OpenAI(base_url=self.base_url, api_key=self.api_key)
            self.async_client = AsyncOpenAI(base_url=self.base_url, api_key=self.api_key)
        self.model = model

    # --- 保留原有的同步调用 ---
    def generate_response(self, system_prompt: str, user_input: str, context: str = "", 
                          temperature: float = 0.7, top_p: float = 1.0, 
                          max_tokens: int = 1000, presence_penalty: float = 0.0, 
                          frequency_penalty: float = 0.0) -> str:
        if not self.api_key or self.api_key == "dummy": return '{"error": "API Key not set"}'
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Context:\n{context}\n\nUser: {user_input}"}
        ]
        try:
            completion = self.client.chat.completions.create(
                model=self.model, messages=messages, temperature=temperature, top_p=top_p,
                max_tokens=max_tokens, presence_penalty=presence_penalty, frequency_penalty=frequency_penalty,
                response_format={"type": "json_object"}
            )
            return completion.choices[0].message.content
        except Exception as e:
            print(f"LLM API Error: {e}")
            return "{}"

    # 🌟 新增：专门为多智能体准备的异步并发调用！
    async def async_generate(self, system_prompt: str, user_input: str, 
                             temperature: float = 0.7, max_tokens: int = 500) -> str:
        if not self.api_key or self.api_key == "dummy": return "{}"
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input}
        ]
        try:
            completion = await self.async_client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                response_format={"type": "json_object"}
            )
            return completion.choices[0].message.content
        except Exception as e:
            print(f"Async LLM API Error: {e}")
            return "{}"