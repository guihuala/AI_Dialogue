from openai import OpenAI
import os
from typing import List, Dict, Optional

class LLMService:
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY") or "dummy"
        self.base_url = os.getenv("LLM_BASE_URL", "https://openrouter.ai/api/v1")
        self.model = model or os.getenv("LLM_MODEL", "x-ai/grok-4.1-fast:free")
        
        self.client = OpenAI(
            base_url=self.base_url,
            api_key=self.api_key,
        )

    def set_api_key(self, api_key: str):
        self.api_key = api_key
        self.client = OpenAI(
            base_url=self.base_url,
            api_key=self.api_key,
        )

    def set_model(self, model: str):
        self.model = model

    def generate_response(self, system_prompt: str, user_input: str, context: str = "") -> str:
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
