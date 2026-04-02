import os
import requests
from dotenv import load_dotenv

load_dotenv()
api_key = os.environ.get("HUGGINGFACE_API_KEY")

payload = {
    "model": "meta-llama/Meta-Llama-3-8B-Instruct",
    "messages": [{"role": "user", "content": "hello"}],
    "max_tokens": 10
}
url = "https://router.huggingface.co/v1/chat/completions"
res = requests.post(url, headers={"Authorization": f"Bearer {api_key}"}, json=payload)
print(res.status_code)
print(res.text[:300])
