from openai import OpenAI
import os

api_key = os.getenv("DEEPSEEK_API_KEY", "sk-99d39b4a26b642989262bc6d377c7ca2")
client = OpenAI(base_url="https://api.deepseek.com/v1", api_key=api_key)

try:
    completion = client.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role": "user", "content": "hello"}]
    )
    print("SUCCESS")
    print(completion.choices[0].message.content)
except Exception as e:
    print("ERROR CAUGHT:")
    import traceback
    traceback.print_exc()
