from openai import OpenAI, AsyncOpenAI
import os
from typing import Optional, Any, Dict, List
from dotenv import load_dotenv
import json

load_dotenv()

class LLMService:
    def __init__(self, api_key: Optional[str] = None, base_url: str = "https://api.deepseek.com/v1", model: str = "deepseek-chat"):
        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY") or "dummy"
        self.base_url = base_url
        self.model = model
        
        self.client = OpenAI(base_url=self.base_url, api_key=self.api_key)
        self.async_client = AsyncOpenAI(base_url=self.base_url, api_key=self.api_key)
        self.typewriter_speed = 30
        self.last_usage = {
            "model": self.model,
            "prompt_tokens": None,
            "completion_tokens": None,
            "total_tokens": None,
        }

    def update_config(self, api_key: Optional[str] = None, base_url: Optional[str] = None, model: Optional[str] = None):
        next_api_key = str(api_key).strip() if api_key is not None else ""
        next_base_url = str(base_url).strip() if base_url is not None else ""
        next_model = str(model).strip() if model is not None else ""

        resolved_api_key = next_api_key or self.api_key or os.getenv("DEEPSEEK_API_KEY") or "dummy"
        resolved_base_url = next_base_url or self.base_url or "https://api.deepseek.com/v1"
        resolved_model = next_model or self.model or "deepseek-chat"

        if resolved_api_key != self.api_key or resolved_base_url != self.base_url:
            self.api_key = resolved_api_key
            self.base_url = resolved_base_url
            self.client = OpenAI(base_url=self.base_url, api_key=self.api_key)
            self.async_client = AsyncOpenAI(base_url=self.base_url, api_key=self.api_key)
        else:
            self.api_key = resolved_api_key
            self.base_url = resolved_base_url
        self.model = resolved_model

    def has_usable_config(self) -> bool:
        return bool(
            str(self.api_key or "").strip()
            and str(self.api_key or "").strip() != "dummy"
            and str(self.base_url or "").strip()
            and str(self.model or "").strip()
        )

    def validate_current_config(self) -> tuple[bool, str]:
        if not self.has_usable_config():
            return False, "尚未完整配置 API Key、网关或模型"

        try:
            self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": "ping"}],
                temperature=0,
                max_tokens=1,
            )
            return True, "配置有效"
        except Exception as e:
            return False, str(e)

    def generate_response(self, system_prompt: str, user_input: str, context: str = "", 
                          temperature: float = 0.7, top_p: float = 1.0, 
                          max_tokens: int = 1000, presence_penalty: float = 0.0, 
                          frequency_penalty: float = 0.0) -> str:
        if not self.api_key or self.api_key == "dummy": return '{"error": "API Key not set"}'
        self.last_usage = {
            "model": self.model,
            "prompt_tokens": None,
            "completion_tokens": None,
            "total_tokens": None,
        }
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Context:\n{context}\n\nUser: {user_input}"}
        ]
        
        # 🌟 自动降级护盾：兼容不支持 json_object 的厂商
        try:
            completion = self.client.chat.completions.create(
                model=self.model, messages=messages, temperature=temperature, top_p=top_p,
                max_tokens=max_tokens, presence_penalty=presence_penalty, frequency_penalty=frequency_penalty,
                response_format={"type": "json_object"}
            )
            usage = getattr(completion, "usage", None)
            self.last_usage = {
                "model": self.model,
                "prompt_tokens": getattr(usage, "prompt_tokens", None) if usage is not None else None,
                "completion_tokens": getattr(usage, "completion_tokens", None) if usage is not None else None,
                "total_tokens": getattr(usage, "total_tokens", None) if usage is not None else None,
            }
            return completion.choices[0].message.content
        except Exception as e:
            error_str = str(e).lower()
            if "response_format" in error_str or "json" in error_str or "not supported" in error_str:
                print(f"⚠️ 当前模型 {self.model} 不支持强 JSON 模式，已自动降级为标准模式生成...")
                try:
                    completion = self.client.chat.completions.create(
                        model=self.model, messages=messages, temperature=temperature, top_p=top_p,
                        max_tokens=max_tokens, presence_penalty=presence_penalty, frequency_penalty=frequency_penalty
                    )
                    usage = getattr(completion, "usage", None)
                    self.last_usage = {
                        "model": self.model,
                        "prompt_tokens": getattr(usage, "prompt_tokens", None) if usage is not None else None,
                        "completion_tokens": getattr(usage, "completion_tokens", None) if usage is not None else None,
                        "total_tokens": getattr(usage, "total_tokens", None) if usage is not None else None,
                    }
                    return completion.choices[0].message.content
                except Exception as inner_e:
                    print(f"LLM 降级生成也失败: {inner_e}")
                    return '{"error": "AI大模型生成失败，请检查 API Key 或网络环境: ' + str(inner_e).replace('"', "'").replace("\n", " ") + '"}'
            print(f"LLM API Error: {e}")
            return '{"error": "AI大模型请求异常: ' + str(e).replace('"', "'").replace("\n", " ") + '"}'

    def generate_response_with_tools(
        self,
        system_prompt: str,
        user_input: str,
        context: str = "",
        temperature: float = 0.7,
        top_p: float = 1.0,
        max_tokens: int = 1000,
        presence_penalty: float = 0.0,
        frequency_penalty: float = 0.0,
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[Any] = "auto",
    ) -> Dict[str, Any]:
        """
        OpenAI-compatible tool calling wrapper.
        返回结构：
        {
          "content": str,
          "tool_calls": [{"name": str, "args": dict}],
          "raw": Any
        }
        """
        if not tools:
            return {
                "content": self.generate_response(
                    system_prompt=system_prompt,
                    user_input=user_input,
                    context=context,
                    temperature=temperature,
                    top_p=top_p,
                    max_tokens=max_tokens,
                    presence_penalty=presence_penalty,
                    frequency_penalty=frequency_penalty,
                ),
                "tool_calls": [],
                "raw": None,
            }
        if not self.api_key or self.api_key == "dummy":
            return {"content": '{"error":"API Key not set"}', "tool_calls": [], "raw": None}

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Context:\n{context}\n\nUser: {user_input}"}
        ]
        try:
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                top_p=top_p,
                max_tokens=max_tokens,
                presence_penalty=presence_penalty,
                frequency_penalty=frequency_penalty,
                response_format={"type": "json_object"},
                tools=tools,
                tool_choice=tool_choice,
            )
            usage = getattr(completion, "usage", None)
            self.last_usage = {
                "model": self.model,
                "prompt_tokens": getattr(usage, "prompt_tokens", None) if usage is not None else None,
                "completion_tokens": getattr(usage, "completion_tokens", None) if usage is not None else None,
                "total_tokens": getattr(usage, "total_tokens", None) if usage is not None else None,
            }
            msg = completion.choices[0].message
            content = getattr(msg, "content", "") or ""
            out_calls: List[Dict[str, Any]] = []
            raw_calls = getattr(msg, "tool_calls", None) or []
            for tc in raw_calls:
                try:
                    fn = getattr(tc, "function", None)
                    name = str(getattr(fn, "name", "") or "").strip()
                    arg_text = getattr(fn, "arguments", "{}") or "{}"
                    args = json.loads(arg_text) if isinstance(arg_text, str) else (arg_text if isinstance(arg_text, dict) else {})
                    if name:
                        out_calls.append({"name": name, "args": args if isinstance(args, dict) else {}})
                except Exception:
                    continue
            return {"content": content, "tool_calls": out_calls, "raw": completion}
        except Exception:
            # 模型不支持工具调用时自动降级为纯文本模式
            return {
                "content": self.generate_response(
                    system_prompt=system_prompt,
                    user_input=user_input,
                    context=context,
                    temperature=temperature,
                    top_p=top_p,
                    max_tokens=max_tokens,
                    presence_penalty=presence_penalty,
                    frequency_penalty=frequency_penalty,
                ),
                "tool_calls": [],
                "raw": None,
            }

    # 在 llm_service.py 的 LLMService 类中新增：

    async def async_generate_response(self, system_prompt: str, user_input: str, 
                                      temperature: float = 0.7, max_tokens: int = 500,
                                      model_override: str = None) -> str:
        """异步生成回答，并支持临时指定使用小模型"""
        
        # 🌟 方案2落地：如果指定了临时模型（如小模型），就用指定的；否则用默认的
        target_model = model_override if model_override else self.model
        
        if not self.api_key or self.api_key == "dummy": return '{"error": "尚未配置 API Key"}'
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input}
        ]
        
        try:
            # 🌟 方案1落地：调用 async_client 实现真正的非阻塞并发
            completion = await self.async_client.chat.completions.create(
                model=target_model, 
                messages=messages, 
                temperature=temperature, 
                max_tokens=max_tokens,
                response_format={"type": "json_object"}
            )
            return completion.choices[0].message.content
        except Exception as e:
            print(f"Async LLM API Error: {e}")
            return '{"error": "AI异步生成失败"}'
