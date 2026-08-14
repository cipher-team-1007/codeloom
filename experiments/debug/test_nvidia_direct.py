import urllib.request
import json
import os

key = "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"
url = "https://integrate.api.nvidia.com/v1/chat/completions"

headers = {
    "Authorization": f"Bearer {key}",
    "Content-Type": "application/json",
    "User-Agent": "CodeLoom-Engine/1.0"
}

payload = {
    "model": "meta/llama-3.3-70b-instruct",
    "messages": [
        {"role": "user", "content": "Respond only with: {\"status\": \"ok\"}"}
    ],
    "temperature": 0.2,
    "max_tokens": 100
}

try:
    req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers=headers)
    with urllib.request.urlopen(req, timeout=10) as resp:
        res = json.loads(resp.read().decode('utf-8'))
        print("Response:", res['choices'][0]['message']['content'])
except Exception as e:
    print("Direct NVIDIA call exception:", e)
