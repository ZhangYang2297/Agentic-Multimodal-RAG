"""测试 Agent 图编译 + 逻辑 + LLM 多后端/熔断（mock 检索结果）"""
import os, sys, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.agent.graph import build_agent
from src.agent.llm import LLMService, _Backend, _is_retryable
from src.agent.llm import CIRCUIT_MIN_CALLS, CIRCUIT_COOLDOWN, TIER_FAST, TIER_DEFAULT, TIER_STRONG
from src.agent.tools import set_engine, router
import openai

# [1] LLM 服务初始化
print("[1] LLM 服务初始化...")
try:
    llm = LLMService(temperature=0.3)
    print(f"   后端数: {len(llm._backends)}")
    for b in llm._backends:
        print(f"     {b.name}: fast={b.resolve_model(TIER_FAST)} "
              f"default={b.resolve_model(TIER_DEFAULT)} strong={b.resolve_model(TIER_STRONG)} "
              f"(可用={b.is_available()})")
except Exception as e:
    print(f"   [X] 初始化失败: {e}")
    llm = None

# [2] Agent 图编译
print("\n[2] Agent 图编译...")
try:
    class MockEngine:
        def search(self, query):
            return [
                {"document": "北京故宫门票60元", "rerank_score": 0.95, "rank": 1},
                {"document": "故宫位于北京中轴线", "rerank_score": 0.88, "rank": 2},
            ]
    mock_engine = MockEngine()
    set_engine(mock_engine)
    if llm:
        build_agent(mock_engine, llm)
        print("   Agent 图编译通过 [OK]")
    else:
        print("   跳过（LLM 不可用）")
except Exception as e:
    print(f"   [X] 编译失败: {e}")
    import traceback; traceback.print_exc()

# [3] 路由逻辑
print("\n[3] 路由逻辑验证...")
for ev, rc, mr, expect in [
    ("relevant", 0, 2, "answer"),
    ("insufficient", 0, 2, "rewrite"),
    ("insufficient", 2, 2, "fallback"),
    ("insufficient", 1, 2, "rewrite"),
    ("not_in_kb", 0, 2, "fallback"),
    ("pending", 0, 2, "fallback"),
]:
    result = router({"evaluation": ev, "retry_count": rc, "max_retries": mr})
    ok = "[OK]" if result == expect else "[X]"
    print(f"   {ok} {ev}/{rc}/{mr} -> {result} (期望 {expect})")
    assert result == expect

# [4] 错误分类
print("\n[4] 可重试错误分类...")
cases = [
    (openai.APITimeoutError, True), (openai.APIConnectionError, True),
    (openai.RateLimitError, True), (openai.BadRequestError, False),
    (openai.AuthenticationError, False), (openai.NotFoundError, False),
    (ValueError, False),
]
for cls, expect in cases:
    e = cls.__new__(cls)
    got = _is_retryable(e)
    ok = "[OK]" if got == expect else "[X]"
    print(f"   {ok} {cls.__name__} -> retryable={got} (期望 {expect})")
    assert got == expect
# 5xx / 429 status errors
for status, expect in [(503, True), (500, True), (429, True), (404, False), (400, False)]:
    e = openai.APIStatusError.__new__(openai.APIStatusError); e.status_code = status
    got = _is_retryable(e)
    ok = "[OK]" if got == expect else "[X]"
    print(f"   {ok} status={status} -> retryable={got} (期望 {expect})")
    assert got == expect

# [5] 滑动窗口熔断状态机
print("\n[5] 滑动窗口熔断验证...")
b = _Backend("T", "k", "http://x", {"default": "m"})
assert b.is_available()
for _ in range(CIRCUIT_MIN_CALLS):
    b.record_failure()
assert not b.is_available(), "100% 错误率应触发熔断"
print(f"   [OK] {CIRCUIT_MIN_CALLS} 次失败 -> 熔断 (available=False)")

b._open_until = time.time() - 1   # 强制冷却结束
assert b.is_available() and b._half_open
print("   [OK] 冷却结束 -> 半开探测")
b.record_failure()
assert not b.is_available()
print("   [OK] 半开探测失败 -> 立即重新熔断")

# 混合：20% 错误率不应熔断
b2 = _Backend("T2", "k", "http://x", {"default": "m"})
for i in range(20):
    b2.record_success() if i % 5 else b2.record_failure()
assert b2.is_available() and abs(b2._error_rate() - 0.2) < 1e-9
print(f"   [OK] 20% 错误率 -> 不熔断 (rate={b2._error_rate():.0%})")

print("\n全部验证完成 [OK]")
