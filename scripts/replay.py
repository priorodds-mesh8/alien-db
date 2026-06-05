#!/usr/bin/env python3
"""Replay a run trace JSONL without calling models (uses the events log).

Usage: python scripts/replay.py runs/<run-id>.jsonl
Prints a human readable reconstruction of the glass-box trace.
"""
import argparse
import json
from pathlib import Path

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("trace", type=Path)
    args = ap.parse_args()

    if not args.trace.exists():
        print(f"No trace at {args.trace}")
        return

    events = [json.loads(line) for line in args.trace.open() if line.strip()]
    print(f"Replaying {len(events)} events from {args.trace.name}\n")
    for ev in events:
        kind = ev.get("kind", "event")
        t = ev.get("t", "")
        if kind == "rag.query.start":
            print(f"[{t}] QUERY START: {ev.get('query')}")
            print(f"  filters: {ev.get('filters')}")
        elif kind == "tool.call":
            print(f"[{t}] TOOL CALL: {ev.get('tool')} args={ev.get('args')}")
        elif kind == "tool.result":
            print(f"[{t}] TOOL RESULT: {ev.get('tool')} -> {ev.get('result_summary')} (latency={ev.get('latency_ms')}ms)")
        elif kind == "synthesis.complete":
            print(f"[{t}] SYNTHESIS: {ev.get('synthesis_preview')}")
        elif kind == "eval.score":
            print(f"[{t}] EVAL: score={ev.get('score')} fabricated={ev.get('fabricated_count')}")
        else:
            print(f"[{t}] {kind}: { {k:v for k,v in ev.items() if k not in ('t','kind','run_id','schema_version')} }")
    print("\nReplay complete (no new LLM calls).")

if __name__ == "__main__":
    main()
