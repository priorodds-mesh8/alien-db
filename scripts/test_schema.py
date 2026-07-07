#!/usr/bin/env python3
"""
Unit tests for the shared stage-boundary schema (no network / no keys).
Run: .venv/bin/python scripts/test_schema.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "packages"))
sys.path.insert(0, str(ROOT / "scripts"))

from uap_corpus.schema import (
    validate_report, validate_chunk, report_is_valid, chunk_is_valid, BOOLEAN_FLAGS,
)
from chunk_and_enrich import build_chunk_metadata

failures = []


def check(name, cond, detail=""):
    print(("  PASS  " if cond else "  FAIL  ") + name + ("" if cond else f"   {detail}"))
    if not cond:
        failures.append(name)


print("Report contract:")
r = validate_report({"id": 12345, "Shape": "ignored-extra", "shape": "Triangle", "narrative": "x"})
check("id coerced int -> str", r.id == "12345" and isinstance(r.id, str))
check("flags default False", all(getattr(r, f) is False for f in BOOLEAN_FLAGS))
check("extra keys allowed (Shape passthrough)", getattr(r, "Shape", None) == "ignored-extra")
ok, err = report_is_valid({"source": "NUFORC"})  # missing required id
check("missing id fails validation", not ok, str(err)[:60])

print("Chunk contract:")
# A chunk built from a validated report metadata should itself validate.
report = {
    "id": "77", "shape": "Disk", "location": "Reno, NV", "observer_count": 2,
    "url": "https://nuforc.org/s/77", "missing_time": True, "landed": True,
}
chunk = {
    "chunk_id": "77-c0", "source_report_id": "77", "source": "NUFORC",
    "chunk_text": "A disk landed in a field near Reno.", "metadata": build_chunk_metadata(report),
    "entities": [], "effects": ["missing time"], "sequence": [],
}
c = validate_chunk(chunk)
check("valid chunk passes", c.chunk_id == "77-c0")
check("metadata threads missing_time flag", c.metadata.missing_time is True)
check("metadata threads landed flag", c.metadata.landed is True)
check("metadata has shape_lc", c.metadata.shape_lc == "disk")
ok, err = chunk_is_valid({**chunk, "chunk_text": "   "})
check("empty chunk_text rejected", not ok, str(err)[:60])
ok2, err2 = chunk_is_valid({"chunk_id": "x", "chunk_text": "hi", "metadata": {}})  # missing source_report_id
check("missing source_report_id rejected", not ok2)

print()
if failures:
    print(f"FAILED: {len(failures)}: {failures}")
    sys.exit(1)
print("ALL SCHEMA CHECKS PASSED")
