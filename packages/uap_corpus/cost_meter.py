"""
Minimal cost meter stub (modeled on agentic-sdr-demo/packages/agents/src/cost-meter.ts).
Logs LLM calls for later aggregation. In real use, integrate with pricing.
"""
import time
from typing import Dict, Any, List

class CostMeter:
    def __init__(self):
        self.calls: List[Dict[str, Any]] = []

    def log_call(self, model: str, input_tokens: int, output_tokens: int, cost_usd: float = 0.0):
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
