"""测试 Agent 图编译 + 逻辑（跳过 embedding，直接 mock 检索结果）"""
import os, sys, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.agent.graph import build_agent
from src.agent.llm import LLMService
from src.agent.tools import set_engine
from src.agent.state import AgentState

# 验证 LLM 服务可初始化
print("[1] LLM 服务初始化...")
try:
    llm = LLMService(temperature=0.3)
    print(f"   模型: {llm.model_name}")
    print(f"   后端数: {len(llm._backends)}")
    for b in llm._backends:
        print(f"     {b.name}: {b.model} (可用={b.is_available()})")
except Exception as e:
    print(f"   ❌ 初始化失败: {e}")
    llm = None

# 验证 Agent 图可编译（即使没有引擎，也要能编译通过）
print("\n[2] Agent 图编译...")
try:
    # Mock 引擎
    class MockEngine:
        def search(self, query):
            return [
                {"document": "北京故宫门票60元", "rerank_score": 0.95, "rank": 1},
                {"document": "故宫位于北京中轴线", "rerank_score": 0.88, "rank": 2},
            ]
    mock_engine = MockEngine()
    set_engine(mock_engine)

    if llm:
        agent = build_agent(mock_engine, llm)
        print("   Agent 图编译通过 ✅")
    else:
        print("   跳过（LLM 不可用）")
except Exception as e:
    print(f"   ❌ 编译失败: {e}")
    import traceback; traceback.print_exc()

# 验证路由逻辑
print("\n[3] 路由逻辑验证...")
from src.agent.tools import router

for ev, rc, mr, expect in [
    ("relevant", 0, 2, "answer"),
    ("insufficient", 0, 2, "rewrite"),
    ("insufficient", 2, 2, "fallback"),  # 超重试上限
    ("insufficient", 1, 2, "rewrite"),   # 还有1次重试
    ("not_in_kb", 0, 2, "fallback"),
    ("pending", 0, 2, "fallback"),       # 未知状态 → fallback
]:
    result = router({"evaluation": ev, "retry_count": rc, "max_retries": mr})
    ok = "✅" if result == expect else "❌"
    print(f"   {ok} {ev}/{rc}/{mr} → {result} (期望 {expect})")

# 验证 LLM 熔断状态机
print("\n[4] 熔断状态机验证...")
if llm and llm._backends:
    b = llm._backends[0]
    print(f"   初始: fail_count={b.fail_count}, available={b.is_available()}")
    for i in range(4):
        b.record_failure()
        print(f"   第{i+1}次失败: fail_count={b.fail_count}, available={b.is_available()}")
    # 不应该重置冷却时间
    from src.agent.llm import CIRCUIT_COOLDOWN_SEC
    print(f"   熔断中, cooldown_until > now: {b.cooldown_until > time.time()}")

print("\n全部验证完成 ✅")
