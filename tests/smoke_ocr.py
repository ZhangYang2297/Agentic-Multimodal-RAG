"""
冒烟脚本 3：百炼 OCR 模型 (qwen3.5-ocr)
统计：耗时 / Token 使用 / 识别结果
"""
import os
import base64
import time
from openai import OpenAI

BASE = "https://llm-mqq0qggh7ed4t502.cn-beijing.maas.aliyuncs.com/compatible-mode/v1"

client = OpenAI(base_url=BASE, api_key=os.environ["DASHSCOPE_API_KEY"])

print("=" * 60)
print("冒烟 3：百炼 OCR  qwen3.5-ocr")
print("=" * 60)

img_path = "data/raw/test_ocr.png"
if not os.path.exists(img_path):
    print(f"❌ 请先放一张带文字的图片到 {img_path}")
    raise SystemExit(1)

with open(img_path, "rb") as f:
    img_b64 = base64.b64encode(f.read()).decode()

t0 = time.perf_counter()
resp = client.chat.completions.create(
    model="qwen3.5-ocr",
    messages=[{
        "role": "user",
        "content": [{
            "type": "image_url",
            "image_url": {"url": f"data:image/png;base64,{img_b64}"}
        }]
    }]
)
elapsed = time.perf_counter() - t0

usage = resp.usage
print(f"⏱️  耗时: {elapsed:.2f}s")
print(f"📊 Token: prompt={usage.prompt_tokens} "
      f"completion={usage.completion_tokens} "
      f"total={usage.total_tokens}")
print(f"📝 识别结果:\n{resp.choices[0].message.content}")
