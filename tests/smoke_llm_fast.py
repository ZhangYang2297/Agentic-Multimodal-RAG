"""
冒烟脚本 2：快速 LLM (qwen3.6-flash)
用途：评分 / 改写等轻量任务
统计：耗时 / Token 使用 / 输出内容
"""
import os
import time
from langchain_openai import ChatOpenAI

BASE = "https://llm-mqq0qggh7ed4t502.cn-beijing.maas.aliyuncs.com/compatible-mode/v1"

llm = ChatOpenAI(
    base_url=BASE,
    api_key=os.environ["DASHSCOPE_API_KEY"],
    model="qwen3.6-flash",
    temperature=0.1,
)

print("=" * 60)
print("冒烟 2：快速 LLM  qwen3.6-flash")
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
