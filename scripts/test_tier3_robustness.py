#!/usr/bin/env python3
"""
Unit tests for the Tier-3 robustness fixes (no network / no API keys / no Pinecone needed).

Run: .venv/bin/python scripts/test_tier3_robustness.py

Covers:
  #9  Pinecone retry — _is_retryable_status / _backoff_seconds decisions
  #10 Resumable seed — fetch_existing_ids no-op on empty input
  #12 Real cost metering — Grok priced non-zero; longest-match; auto-price on log_call
  #13 Embedder — empty query rejected instead of a degenerate zero vector
"""
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "packages"))

from uap_corpus.cost_meter import CostMeter, estimate_cost, price_for_model
from uap_corpus.pinecone_client import _is_retryable_status, _backoff_seconds
from uap_corpus.embedder import embed_query

failures = []


def check(name, cond, detail=""):
    print(("  PASS  " if cond else "  FAIL  ") + name + ("" if cond else f"   {detail}"))
    if not cond:
        failures.append(name)


# ---------------------------------------------------------------- #12 cost metering
print("#12 cost metering (Grok no longer logs $0):")
grok_cost = estimate_cost("grok-4.3", 1000, 1000)
check("grok call is priced non-zero", grok_cost > 0, f"cost={grok_cost}")
check("output tokens cost more than input", estimate_cost("grok-4.3", 0, 1000) > estimate_cost("grok-4.3", 1000, 0))
check("longest-match wins (claude-3-5-haiku over generic)", price_for_model("claude-3-5-haiku-latest") == (0.80, 4.00),
      str(price_for_model("claude-3-5-haiku-latest")))
check("unknown model falls back to non-zero default", estimate_cost("some-mystery-model", 1000, 1000) > 0)
m = CostMeter()
m.log_call("grok-4.3", 500, 500)  # no explicit cost -> must auto-price, not default to 0
check("log_call auto-prices when cost omitted", m.total_cost() > 0, f"total={m.total_cost()}")
m2 = CostMeter()
m2.log_call("free-local", 0, 0)
check("zero-token local call costs $0", m2.total_cost() == 0)


# ---------------------------------------------------------------- #9 retry policy
print("#9 Pinecone retry/backoff:")
check("429 is retryable", _is_retryable_status(429))
check("503 is retryable", _is_retryable_status(503))
check("400 is NOT retryable", not _is_retryable_status(400))
check("404 is NOT retryable", not _is_retryable_status(404))
# full-jitter backoff stays within [0, cap] and the ceiling grows with attempts
for a in range(6):
    b = _backoff_seconds(a, base=0.5, cap=30.0)
    if not (0 <= b <= 30.0):
        check(f"backoff bounded at attempt {a}", False, f"b={b}")
        break
else:
    check("backoff always within [0, cap]", True)
check("later attempts allow larger max backoff",
      max(_backoff_seconds(5) for _ in range(200)) > max(_backoff_seconds(0) for _ in range(200)))


# ---------------------------------------------------------------- #13 embedder empty-query guard
print("#13 embedder rejects empty query:")
raised = False
try:
    embed_query("   ")
except ValueError:
    raised = True
except Exception as e:  # torch not needed: empty check precedes model load
    raised = False
    print(f"    (unexpected: {type(e).__name__})")
check("embed_query('   ') raises ValueError (no zero vector)", raised)


# ---------------------------------------------------------------- #10 resumable seed no-op
print("#10 resumable seed helper:")
from uap_corpus.pinecone_client import PineconeClient
client = PineconeClient(api_key="test-key")  # no network call for empty input
check("fetch_existing_ids([]) -> empty set without network", client.fetch_existing_ids([]) == set())


print()
if failures:
    print(f"FAILED: {len(failures)} check(s): {failures}")
    sys.exit(1)
print("ALL TIER-3 ROBUSTNESS CHECKS PASSED")
