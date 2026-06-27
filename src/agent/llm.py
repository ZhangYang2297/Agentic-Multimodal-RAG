"""LLM 服务封装 - 多后端降级 + 模型分级路由 + 可重试分类 + 滑动窗口熔断

设计要点（对齐企业级做法）:
  1. 分级超时：fast/default/strong 三档不同 timeout，避免小任务等大模型。
  2. 重试分类：只对「可重试错误」(429/5xx/超时/网络) 退避重试；
     「不可重试错误」(400/401/403/404/内容审核) 立即放弃，不空烧 token。
  3. 退避抖动：指数退避 + full jitter，避免并发重试风暴。
  4. 多后端降级：DashScope(主) → Volcengine ARK(备)，主后端熔断时自动切换。
  5. 滑动窗口熔断：按「最近 N 次调用错误率」触发，而非「连续失败计数」，
     并支持 half-open 探测（冷却结束放一次探测，失败立即重新熔断）。
"""
import os, json, time, random, re
from collections import deque
from typing import Optional

import openai
from openai import OpenAI


# ─── 模型分级（tier），各后端按自己的命名解析 ───
TIER_FAST = "fast"
TIER_DEFAULT = "default"
TIER_STRONG = "strong"

# ─── 分级超时（秒）：高频轻量任务短超时，重质量任务略长 ───
TIER_TIMEOUT = {
    TIER_FAST: float(os.environ.get("AGENT_TIMEOUT_FAST", 15)),
    TIER_DEFAULT: float(os.environ.get("AGENT_TIMEOUT_DEFAULT", 20)),
    TIER_STRONG: float(os.environ.get("AGENT_TIMEOUT_STRONG", 25)),
}

# ─── 重试配置 ───
MAX_RETRIES = int(os.environ.get("AGENT_MAX_RETRIES", 2))   # 单后端单次调用最多重试次数
BACKOFF_BASE = 0.5      # 退避基数（秒）
BACKOFF_CAP = 8.0       # 退避上限（秒）

# ─── 滑动窗口熔断配置 ───
CIRCUIT_WINDOW = int(os.environ.get("AGENT_CIRCUIT_WINDOW", 20))   # 统计窗口大小
CIRCUIT_MIN_CALLS = int(os.environ.get("AGENT_CIRCUIT_MIN_CALLS", 5))  # 窗口内最小样本数才参与判断
CIRCUIT_ERROR_RATE = float(os.environ.get("AGENT_CIRCUIT_ERROR_RATE", 0.5))  # 错误率阈值
CIRCUIT_COOLDOWN = float(os.environ.get("AGENT_CIRCUIT_COOLDOWN", 60))  # 熔断冷却时间（秒）


# ─── 错误分类 ───
def _is_retryable(exc: Exception) -> bool:
    """判断异常是否值得重试。

    可重试：超时、网络连接、限流(429)、服务端 5xx。
    不可重试：参数错误(400)、鉴权(401)、权限(403)、不存在(404)、内容审核等。
    """
    if isinstance(exc, (openai.APITimeoutError, openai.APIConnectionError, openai.RateLimitError)):
        return True
    if isinstance(exc, (openai.BadRequestError, openai.AuthenticationError,
                        openai.PermissionDeniedError, openai.NotFoundError)):
        return False
    if isinstance(exc, openai.APIStatusError):
        status = getattr(exc, "status_code", None)
        if status is None:
            return False
        return status == 429 or status >= 500
    # 未知异常保守处理：不重试，避免空烧
    return False


def _retry_after(exc: Exception) -> Optional[float]:
    """从 429 响应里读取 Retry-After（秒），读不到返回 None。"""
    resp = getattr(exc, "response", None)
    if resp is None:
        return None
    try:
        val = resp.headers.get("retry-after")
        return float(val) if val is not None else None
    except (AttributeError, ValueError, TypeError):
        return None


class _Backend:
    """单个 LLM 后端：持有 client、模型分级表、滑动窗口熔断状态。"""

    def __init__(self, name: str, api_key: str, base_url: str, model_map: dict, extra: dict = None):
        self.name = name
        self.client = OpenAI(base_url=base_url, api_key=api_key)
        self.model_map = model_map          # {tier: model_name}
        self.extra = extra or {}
        self._window = deque(maxlen=CIRCUIT_WINDOW)  # True=成功 False=失败
        self._open_until = 0.0              # 熔断打开到期时间戳
        self._half_open = False             # 是否处于半开探测

    def resolve_model(self, tier: str) -> str:
        return self.model_map.get(tier, self.model_map[TIER_DEFAULT])

    def is_available(self) -> bool:
        now = time.time()
        if self._open_until > now:
            return False  # 熔断冷却中
        if self._open_until and self._open_until <= now:
            # 冷却结束 → 进入半开，放一次探测
            self._half_open = True
            self._open_until = 0.0
        return True

    def _error_rate(self) -> float:
        if len(self._window) < CIRCUIT_MIN_CALLS:
            return 0.0
        fails = sum(1 for ok in self._window if not ok)
        return fails / len(self._window)

    def record_success(self):
        if self._half_open:
            # 半开探测成功 → 闭合，清空窗口重新统计
            self._half_open = False
            self._window.clear()
        self._window.append(True)

    def record_failure(self):
        if self._half_open:
            # 半开探测失败 → 立即重新熔断
            self._half_open = False
            self._open_until = time.time() + CIRCUIT_COOLDOWN
            self._window.clear()
            print(f"    [WARN]  [CircuitBreaker] {self.name} 半开探测失败，重新熔断 {CIRCUIT_COOLDOWN:.0f}s")
            return
        self._window.append(False)
        if self._error_rate() > CIRCUIT_ERROR_RATE:
            self._open_until = time.time() + CIRCUIT_COOLDOWN
            rate = self._error_rate()
            print(f"    [WARN]  [CircuitBreaker] {self.name} 错误率 {rate:.0%} 超阈值，熔断 {CIRCUIT_COOLDOWN:.0f}s")
            self._window.clear()


class LLMService:
    """LLM 服务 - 多后端降级 + 模型分级路由 + 可重试分类 + 滑动窗口熔断。

    后端优先级（按注册顺序）:
      1. DashScope 百炼（主）
      2. Volcengine ARK 方舟（备）
    至少需要其中一个的 API Key。
    """

    def __init__(self, temperature: float = 0.3):
        self.temperature = temperature
        self._backends = []
        self._init_backends()

    def _init_backends(self):
        # 主：DashScope 百炼
        ds_key = os.environ.get("DASHSCOPE_API_KEY", "")
        if ds_key:
            self._backends.append(_Backend(
                "DashScope", ds_key,
                "https://dashscope.aliyuncs.com/compatible-mode/v1",
                model_map={
                    TIER_FAST: os.environ.get("AGENT_FAST_MODEL", "qwen3.6-flash"),
                    TIER_DEFAULT: os.environ.get("AGENT_MODEL", "qwen3.7-plus"),
                    TIER_STRONG: os.environ.get("AGENT_STRONG_MODEL", "deepseek-v4-pro"),
                },
                extra={"enable_thinking": False},  # DashScope 私有参数：关闭深度思考
            ))

        # 备：Volcengine ARK 方舟
        ark_key = os.environ.get("ARK_API_KEY", "")
        if ark_key:
            self._backends.append(_Backend(
                "ARK", ark_key,
                "https://ark.cn-beijing.volces.com/api/v3",
                model_map={
                    TIER_FAST: os.environ.get("ARK_FAST_MODEL", "doubao-seed-1-6-flash-250828"),
                    TIER_DEFAULT: os.environ.get("ARK_MODEL", "doubao-seed-2-0-mini-260428"),
                    TIER_STRONG: os.environ.get("ARK_STRONG_MODEL", "deepseek-v3-2-251201"),
                },
            ))

        if not self._backends:
            raise EnvironmentError(
                "未找到可用的 API Key。请设置 DASHSCOPE_API_KEY 或 ARK_API_KEY"
            )

    def _call(self, messages: list, tier: str = TIER_DEFAULT) -> str:
        """调用 LLM：多后端降级 + 可重试分类 + 退避抖动 + 滑动窗口熔断。"""
        timeout = TIER_TIMEOUT.get(tier, TIER_TIMEOUT[TIER_DEFAULT])
        last_error = None
        tried_any = False

        for backend in self._backends:
            if not backend.is_available():
                continue
            tried_any = True
            model = backend.resolve_model(tier)

            for attempt in range(1, MAX_RETRIES + 1):
                try:
                    kwargs = {
                        "model": model,
                        "messages": messages,
                        "temperature": self.temperature,
                        "timeout": timeout,
                    }
                    if backend.extra:
                        kwargs["extra_body"] = backend.extra
                    resp = backend.client.chat.completions.create(**kwargs)
                    backend.record_success()
                    return resp.choices[0].message.content.strip()
                except Exception as e:
                    last_error = e
                    retryable = _is_retryable(e)
                    backend.record_failure()
                    if not retryable:
                        # 不可重试：放弃当前后端，直接尝试下一个后端
                        print(f"    [FAIL] {backend.name}/{model} 不可重试错误，切换后端 ({type(e).__name__})")
                        break
                    if attempt < MAX_RETRIES:
                        wait = _retry_after(e) or min(BACKOFF_CAP, BACKOFF_BASE * (2 ** (attempt - 1)))
                        wait += random.uniform(0, BACKOFF_BASE)  # full jitter
                        print(f"    [WARN]  {backend.name}/{model} 第{attempt}次失败 ({type(e).__name__})，{wait:.1f}s 重试")
                        time.sleep(wait)
                    else:
                        print(f"    [FAIL] {backend.name}/{model} 重试耗尽，切换后端")

        if not tried_any:
            raise RuntimeError("所有 LLM 后端均处于熔断冷却中，请稍后重试")
        raise RuntimeError(f"所有 LLM 后端均不可用: {last_error}")

    # ─── 公开接口：按 tier 路由 ───

    def chat(self, system: str, user: str) -> str:
        """默认模型档。"""
        return self._call([
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ], tier=TIER_DEFAULT)

    def chat_fast(self, system: str, user: str) -> str:
        """快速模型档（evaluate/rewrite 等高频轻量任务）。"""
        return self._call([
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ], tier=TIER_FAST)

    def chat_strong(self, system: str, user: str) -> str:
        """强模型档（answer/fallback 等重质量任务）。"""
        return self._call([
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ], tier=TIER_STRONG)

    def chat_json(self, system: str, user: str) -> dict:
        return self._parse_json(self.chat(system, user))

    def chat_fast_json(self, system: str, user: str) -> dict:
        return self._parse_json(self.chat_fast(system, user))

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
