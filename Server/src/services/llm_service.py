from openai import OpenAI
import os
from typing import Optional
from dotenv import load_dotenv

# 🌟 自动加载项目根目录下的 .env 文件
load_dotenv()

class LLMService:
    def __init__(self, api_key: Optional[str] = None, base_url: str = "[https://api.deepseek.com/v1](https://api.deepseek.com/v1)", model: str = "deepseek-chat"):
        # 🌟 优先使用传入的 api_key，其次读取 DEEPSEEK_API_KEY，最后使用 dummy
        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY") or "dummy"
        self.base_url = base_url
        self.model = model
        self.client = OpenAI(
            base_url=self.base_url,
            api_key=self.api_key,
        )

    def update_config(self, api_key: str, base_url: str, model: str):
        """动态更新 API 配置"""
        # 如果前端 UI 传入了空的 API Key，则回退到环境变量里的默认 Key
        if not api_key:
            api_key = os.getenv("DEEPSEEK_API_KEY") or "dummy"
            
        # 只有当 key 或 url 发生变化时才重新实例化 Client，节省开销
        if api_key != self.api_key or base_url != self.base_url:
            self.api_key = api_key
            self.base_url = base_url
            self.client = OpenAI(
                base_url=self.base_url,
                api_key=self.api_key,
            )
        self.model = model

    def generate_response(self, system_prompt: str, user_input: str, context: str = "", 
                          temperature: float = 0.7, top_p: float = 1.0, 
                          max_tokens: int = 1000, presence_penalty: float = 0.0, 
                          frequency_penalty: float = 0.0) -> str:
        
        if not self.api_key or self.api_key == "dummy":
            return '{"narrator_transition": "Error: API Key not set. Please configure in UI or .env file.", "dialogue_sequence": [], "next_options": [], "stat_changes": {}, "is_end": false}'

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Context:\n{context}\n\nUser: {user_input}"}
        ]

        try:
            # 🌟 核心跨越：强制要求 API 锁定 JSON 输出模式！
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                top_p=top_p,
                max_tokens=max_tokens,
                presence_penalty=presence_penalty,
                frequency_penalty=frequency_penalty,
                response_format={"type": "json_object"} # 👈 就是这一个神仙参数！
            )
            return completion.choices[0].message.content
        except Exception as e:
            print(f"LLM API Error: {e}")
            return '{"narrator_transition": "系统接口请求失败，请检查网络或 API Key。", "dialogue_sequence": [], "next_options": ["【重试】"], "stat_changes": {}, "is_end": false}'