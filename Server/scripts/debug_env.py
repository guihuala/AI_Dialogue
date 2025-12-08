import os
from dotenv import load_dotenv

# Try to load .env from the current directory (Server/)
load_dotenv()

key = os.getenv("OPENROUTER_API_KEY")

print(f"Current Working Directory: {os.getcwd()}")
print(f"Checking for .env file: {os.path.exists('.env')}")

if key:
    print(f"API Key found! Length: {len(key)}")
    print(f"Key starts with: {key[:10]}...")
    if key == "sk-or-v1-your-key-here":
        print("WARNING: You are using the placeholder key!")
    elif key == "dummy":
        print("WARNING: You are using the dummy key!")
else:
    print("ERROR: OPENROUTER_API_KEY not found in environment variables.")
