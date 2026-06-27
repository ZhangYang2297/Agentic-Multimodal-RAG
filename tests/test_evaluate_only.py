import os, sys, time
sys.path.insert(0, "C:/Users/admin/Documents/Agentic-Multimodal-RAG")
from src.agent.llm import LLMService

llm = LLMService(temperature=0.3)

system = (
    "你是一个检索质量评估专家。判断检索到的内容是否能回答用户问题。\n"
    "返回 JSON:\n"
    '{"judgment": "relevant" | "insufficient" | "not_in_kb", "reason": "简要说明判断理由"}'
)
user = (
    "用户问题：成都有哪些必去的旅游景点？\n\n"
    "检索结果：\n"
    "[1] 成都必去的景点包括宽窄巷子、锦里、武侯祠、杜甫草堂等。\n"
    "[2] 青城山都江堰是成都周边最著名的景点之一。\n"
    "[3] 成都美食以火锅、串串、担担面闻名。\n\n"
    "请判断这些检索结果是否能回答用户问题。"
)

print(f"System: {len(system)} chars, User: {len(user)} chars")
print("Calling chat_fast_json...")
t0 = time.perf_counter()
try:
    result = llm.chat_fast_json(system, user)
    elapsed = time.perf_counter() - t0
    print(f"Success! {elapsed:.2f}s")
    print(result)
except Exception as e:
    elapsed = time.perf_counter() - t0
    print(f"Failed after {elapsed:.2f}s: {type(e).__name__}: {str(e)[:200]}")
    import traceback
    traceback.print_exc()
