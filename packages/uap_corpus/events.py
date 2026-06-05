"""
Minimal JSONL event writer (modeled on ~/agentic-sdr-demo/packages/events).
Used for glass-box traces of ingest runs and analysis queries.
"""
import json
import time
from pathlib import Path
from typing import Dict, Any

RUNS_DIR = Path("runs")
RUNS_DIR.mkdir(exist_ok=True)

def write_event(run_id: str, kind: str, payload: Dict[str, Any]) -> None:
    ev = {
        "schema_version": "1",
        "t": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "run_id": run_id,
        "kind": kind,
        **payload,
    }
    p = RUNS_DIR / f"{run_id}.jsonl"
    with p.open("a") as f:
        f.write(json.dumps(ev, ensure_ascii=False) + "\n")

def new_run_id(prefix: str = "uap") -> str:
    return f"{prefix}-{int(time.time())}"
