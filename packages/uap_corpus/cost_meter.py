"""
Cost meter (modeled on agentic-sdr-demo/packages/agents/src/cost-meter.ts).
Logs LLM calls and prices them from real token usage. The prototype previously logged a flat
`0.001 if ANTHROPIC_KEY else 0.0`, which meant the default Grok path recorded $0 for every paid
call — the meter lied. `estimate_cost` prices from a per-model table so the meter reflects reality.
"""
import time
from typing import Dict, Any, List, Tuple

# Approximate list prices in USD per 1M tokens: (input, output). Keys are matched as substrings of
# the model id (longest match wins) so "grok-4.3" and "grok-4.20-...-reasoning" both resolve. Update
# as vendor pricing changes; unknown models fall back to _DEFAULT_PRICE (clearly non-zero, not free).
_PRICE_PER_M: Dict[str, Tuple[float, float]] = {
    "grok-4": (5.00, 15.00),
    "grok-beta": (5.00, 15.00),
    "grok": (5.00, 15.00),
    "claude-3-haiku": (0.25, 1.25),
    "claude-3-5-haiku": (0.80, 4.00),
    "claude-haiku-4": (1.00, 5.00),
    "claude-3-5-sonnet": (3.00, 15.00),
    "claude-sonnet": (3.00, 15.00),
    "claude-opus": (15.00, 75.00),
    "gpt-4o-mini": (0.15, 0.60),
    "gpt-4o": (2.50, 10.00),
}
_DEFAULT_PRICE: Tuple[float, float] = (5.00, 15.00)


def price_for_model(model: str) -> Tuple[float, float]:
    """(input, output) USD per 1M tokens for a model id, longest substring match wins."""
    m = (model or "").lower()
    best_key, best_len = None, -1
    for key in _PRICE_PER_M:
        if key in m and len(key) > best_len:
            best_key, best_len = key, len(key)
    return _PRICE_PER_M[best_key] if best_key else _DEFAULT_PRICE


def estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Price a call from token usage. Never returns 0 for a real (nonzero-token) call unless the
    model genuinely costs nothing."""
    pin, pout = price_for_model(model)
    return (max(0, input_tokens) / 1_000_000.0) * pin + (max(0, output_tokens) / 1_000_000.0) * pout


class CostMeter:
    def __init__(self):
        self.calls: List[Dict[str, Any]] = []

    def log_call(self, model: str, input_tokens: int, output_tokens: int, cost_usd: float = None):
        # If the caller doesn't supply a cost, price it from the per-model table instead of $0.
        if cost_usd is None:
            cost_usd = estimate_cost(model, input_tokens, output_tokens)
        self.calls.append({
            "t": time.time(),
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost_usd": cost_usd,
        })

    def total_cost(self) -> float:
        return sum(c["cost_usd"] for c in self.calls)

    def summary(self) -> Dict[str, Any]:
        return {
            "total_calls": len(self.calls),
            "total_cost_usd": round(self.total_cost(), 4),
            "calls": self.calls,
        }

# Global for simple use in prototype
GLOBAL_METER = CostMeter()
