"""
冒烟脚本 1：主推理 LLM (qwen3.7-max-2026-06-08)
统计：耗时 / Token 使用 / 输出内容
"""
import os
import time
from langchain_openai import ChatOpenAI

BASE = "https://llm-mqq0qggh7ed4t502.cn-beijing.maas.aliyuncs.com/compatible-mode/v1"

llm = ChatOpenAI(
    base_url=BASE,
    api_key=os.environ["DASHSCOPE_API_KEY"],
    model="qwen3.7-max-2026-06-08",
    temperature=0.3,
)

print("=" * 60)
print("冒烟 1：主推理 LLM  qwen3.7-max-2026-06-08")
print("=" * 60)

t0 = time.perf_counter()
resp = llm.invoke("用一句话介绍北京故宫。")
elapsed = time.perf_counter() - t0

usage = resp.response_metadata.get("token_usage", {})
print(f"⏱️  耗时: {elapsed:.2f}s")
print(f"📊 Token: prompt={usage.get('prompt_tokens')} "
      f"completion={usage.get('completion_tokens')} "
      f"total={usage.get('total_tokens')}")
print(f"📝 内容: {resp.content}")
