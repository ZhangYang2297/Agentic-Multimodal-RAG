"""LLM 服务封装 - DashScope 主后端 + 多模型路由 + 重试 + 熔断"""
import os, json, time, re
from typing import Optional
from openai import OpenAI


# ─── 模型配置（优先用百炼 DashScope） ───
FAST_MODEL = os.environ.get("AGENT_FAST_MODEL", "qwen3.6-flash")
DEFAULT_MODEL = os.environ.get("AGENT_MODEL", "qwen3.7-plus")
STRONG_MODEL = os.environ.get("AGENT_STRONG_MODEL", "deepseek-v4-pro")

# ─── 重试/熔断配置 ───
MAX_RETRIES = 3
CIRCUIT_THRESHOLD = 3
CIRCUIT_COOLDOWN = 60
REQUEST_TIMEOUT = 30


class _Backend:
    def __init__(self, name: str, api_key: str, base_url: str, model: str, extra: dict = None):
        self.name = name
        self.client = OpenAI(base_url=base_url, api_key=api_key, timeout=REQUEST_TIMEOUT)
        self.model = model
        self.extra = extra or {}
        self.fail_count = 0
        self.cooldown_until = 0.0

    def is_available(self) -> bool:
        if self.fail_count >= CIRCUIT_THRESHOLD:
            if time.time() < self.cooldown_until:
                return False
            self.fail_count = 0
        return True

    def record_failure(self):
        self.fail_count += 1
        if self.fail_count >= CIRCUIT_THRESHOLD:
            self.cooldown_until = time.time() + CIRCUIT_COOLDOWN
            print(f"    [WARN]  [CircuitBreaker] {self.name} 熔断 {CIRCUIT_COOLDOWN}s")

    def record_success(self):
        self.fail_count = 0


class LLMService:
    """
    LLM 服务 - 支持多模型路由 + 多后端降级 + 重试 + 熔断

    模型路由（可通过环境变量覆盖）:
      - AGENT_FAST_MODEL    = qwen3.6-flash   → evaluate/rewrite
      - AGENT_MODEL         = qwen3.7-plus    → 默认
      - AGENT_STRONG_MODEL  = deepseek-v4-pro → answer/fallback

    后端:
      仅 DashScope 百炼（SiliconFlow 仅用于 embedding/reranker，不做 LLM）
    """

    def __init__(self, temperature: float = 0.3):
        self.temperature = temperature
        self._backends = []
        self._init_backends()

    def _init_backends(self):
        """注册所有可用后端"""
        # 主：DashScope 百炼
        ds_key = os.environ.get("DASHSCOPE_API_KEY", "")
        if ds_key:
            self._backends.append(
                _Backend("DashScope", ds_key,
                         "https://dashscope.aliyuncs.com/compatible-mode/v1",
                         DEFAULT_MODEL, extra={"enable_thinking": False})
            )
        # 注意：SiliconFlow 仅用于 embedding(BAAI/bge-m3) 和 reranker(BAAI/bge-reranker-v2-m3)
        # LLM 统一走 DashScope 百炼，不使用 SiliconFlow 的 chat 模型
        if not self._backends:
            raise EnvironmentError(
                "未找到可用的 API Key。请设置 DASHSCOPE_API_KEY"
            )

    def _call(self, messages: list, model: str = None) -> str:
        """调用 LLM（自动降级 + 重试 + 熔断）"""
        last_error = None
        for backend in self._backends:
            if not backend.is_available():
                continue
            actual_model = model or backend.model
            for attempt in range(1, MAX_RETRIES + 1):
                try:
                    kwargs = {"model": actual_model, "messages": messages, "temperature": self.temperature}
                    if backend.extra:
                        kwargs["extra_body"] = backend.extra
                    resp = backend.client.chat.completions.create(**kwargs)
                    backend.record_success()
                    return resp.choices[0].message.content.strip()
                except Exception as e:
                    last_error = e
                    if attempt < MAX_RETRIES:
                        wait = 2 ** attempt
                        print(f"    [WARN]  {backend.name}/{actual_model} 第{attempt}次失败 ({e}), {wait}s重试")
                        time.sleep(wait)
                    else:
                        print(f"    [FAIL] {backend.name}/{actual_model} 重试耗尽")
                        backend.record_failure()
        raise RuntimeError(f"所有 LLM 后端均不可用: {last_error}")

    # ─── 公开接口：不同模型路由 ───

    def chat(self, system: str, user: str) -> str:
        """默认模型（qwen3.7-plus）"""
        return self._call([
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ])

    def chat_fast(self, system: str, user: str) -> str:
        """快速模型（qwen3.6-flash）"""
        return self._call([
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ], model=FAST_MODEL)

    def chat_strong(self, system: str, user: str) -> str:
        """强模型（qwen3.7-max）"""
        return self._call([
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ], model=STRONG_MODEL)

    def chat_json(self, system: str, user: str) -> dict:
        """默认模型 + JSON 解析"""
        text = self.chat(system, user)
        return self._parse_json(text)

    def chat_fast_json(self, system: str, user: str) -> dict:
        """快速模型 + JSON 解析"""
        text = self.chat_fast(system, user)
        return self._parse_json(text)

    # ─── 工具方法 ───

    @staticmethod
    def _parse_json(text: str) -> dict:
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        if m:
            return json.loads(m.group(1))
        m = re.search(r"(\{.*\})", text, re.DOTALL)
        if m:
            return json.loads(m.group(1))
        raise ValueError(f"LLM 返回非 JSON: {text[:200]}")

    @staticmethod
    def truncate(text: str, max_chars: int = 2000) -> str:
        if len(text) <= max_chars:
            return text
        cut = text[:max_chars]
        last = cut.rfind("。")
        if last > max_chars // 2:
            return cut[:last + 1] + "\n\n...（内容已截断）"
        return cut + "\n\n...（内容已截断）"
