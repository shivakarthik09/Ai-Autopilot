import os
from dotenv import load_dotenv
from openai import OpenAI
import litellm
from litellm import completion

# Use absolute path to .env file
env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(dotenv_path=env_path, override=True)
print(f'OPENAI_API_KEY after load_dotenv: {os.getenv("OPENAI_API_KEY")}')

api_key = os.getenv("OPENAI_API_KEY")

if not api_key:
    print("OPENAI_API_KEY not found in environment.")
    exit(1)

# Test with OpenAI client directly
try:
    client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Say hello!"}
        ]
    )
    print("\nOpenAI API call succeeded. Response:")
    print(response.choices[0].message.content)
except Exception as e:
    print(f"\nOpenAI API call failed: {e}")

# Test with LiteLLM
try:
    litellm.api_key = api_key
    response = completion(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Say hello using LiteLLM!"}
        ]
    )
    print("\nLiteLLM API call succeeded. Response:")
    print(response.choices[0].message.content)
except Exception as e:
    print(f"\nLiteLLM API call failed: {e}") 