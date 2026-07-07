#!/usr/bin/env python3
"""
Unit tests for the Tier-1 glass-box integrity fixes.

Run: python scripts/test_tier1_integrity.py   (no network / no API keys / no Pinecone needed)

Covers:
  #1 fabrication_eval  — no 0.6 floor; a fabricated specific scores low and is flagged
  #2 _local_synthesize — no hardcoded gray-alien "analysis" paragraph; static caveat is tagged
  #3 build_shape_filter — case-robust $in so a lowercase dropdown matches Title-case metadata
  #5 build_chunk_metadata — all six boolean flags threaded through (not just possible_abduction)
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "packages"))
sys.path.insert(0, str(ROOT / "scripts"))

from uap_corpus.fabrication import fabrication_eval, build_shape_filter
from chunk_and_enrich import build_chunk_metadata, BOOLEAN_FLAGS

failures = []


def check(name, cond, detail=""):
    if cond:
        print(f"  PASS  {name}")
    else:
        print(f"  FAIL  {name}  {detail}")
        failures.append(name)


# ---------------------------------------------------------------- #1 fabrication_eval
print("#1 fabrication_eval (no floor, claim-level):")
evidence = [
    "A silent triangular craft with three white lights hovered over the field for two minutes.",
    "The object made no sound and then moved away quickly to the north.",
]

# Fabricated: invents a named being + a precise time absent from evidence
fabricated_synth = (
    "The witness named the being Zoran and recorded the exact time 03:17. "
    "A government cover-up team arrived in black helicopters afterward."
)
res_fab = fabrication_eval(fabricated_synth, evidence)
check("fabricated synthesis scores below 0.6", res_fab["score"] < 0.6, f"score={res_fab['score']}")
check("fabricated synthesis is not floored at 0.6", res_fab["score"] != 0.6, f"score={res_fab['score']}")
check("flags the invented specifics", len(res_fab["fabricated"]) >= 1, str(res_fab["fabricated"]))

# Well-grounded: restates only what the evidence says
grounded_synth = (
    "The reports describe a silent triangular craft with white lights that hovered over a field. "
    "The object made no sound and then moved away."
)
res_ok = fabrication_eval(grounded_synth, evidence)
check("grounded synthesis scores high", res_ok["score"] >= 0.8, f"score={res_ok['score']}")

# A perfectly-clean run can exceed the old 0.98 cap
check("no artificial 0.98 cap", res_ok["score"] > 0.98 or res_ok["score"] == 1.0, f"score={res_ok['score']}")

# [STATIC]-tagged lines are ignored (methodological caveat, not a claim about evidence)
static_synth = "[STATIC] Sleep paralysis and Hopkins-era narratives may explain many such Zoran reports."
res_static = fabrication_eval(static_synth, evidence)
check("[STATIC] lines are excluded from scoring", res_static["claims"] == [], str(res_static["claims"]))

# empty / trivial synthesis doesn't crash and isn't penalized
res_empty = fabrication_eval("", evidence)
check("empty synthesis -> score 1.0", res_empty["score"] == 1.0, str(res_empty))


# ---------------------------------------------------------------- #3 build_shape_filter
print("#3 build_shape_filter (case-robust):")
f = build_shape_filter("triangle")
variants = set(f.get("shape", {}).get("$in", []))
check("lowercase input matches Title-case metadata", "Triangle" in variants and "triangle" in variants, str(variants))
check("uses $in (not case-sensitive $eq)", "$in" in f.get("shape", {}), str(f))
check("empty shape -> no filter", build_shape_filter("") == {} and build_shape_filter("   ") == {})


# ---------------------------------------------------------------- #5 build_chunk_metadata
print("#5 build_chunk_metadata (all flags threaded):")
report = {
    "occurred": "1998-03-01", "location": "Phoenix, AZ, USA", "shape": "Triangle",
    "observer_count": 3, "url": "https://nuforc.org/sighting/12345",
    "possible_abduction": True, "missing_time": True, "marks_on_body": False,
    "landed": False, "lights_on_object": True, "animals_reacted": True,
}
md = build_chunk_metadata(report)
for flag in BOOLEAN_FLAGS:
    check(f"metadata carries flag '{flag}'", flag in md and isinstance(md[flag], bool), str(md.get(flag)))
check("shape_lc present for durable case-insensitive filter", md.get("shape_lc") == "triangle", str(md.get("shape_lc")))
check("url threaded (needed by Report Drawer)", md.get("url", "").startswith("https://"), str(md.get("url")))
check("six boolean flags in total", sum(1 for k in BOOLEAN_FLAGS if k in md) == 6)


# ---------------------------------------------------------------- #2 _local_synthesize source scan
print("#2 _local_synthesize (no hardcoded archetype prose):")
app_src = (ROOT / "ui" / "app.py").read_text()
banned = "close-range encounters with small gray or humanoid figures"
check("hardcoded gray-alien 'analysis' paragraph removed", banned not in app_src)
check("derives pattern notes from chunks", "Pattern notes (derived from these" in app_src)
check("static caveat is [STATIC]-tagged", "[STATIC]" in app_src)


print()
if failures:
    print(f"FAILED: {len(failures)} check(s): {failures}")
    sys.exit(1)
print("ALL TIER-1 INTEGRITY CHECKS PASSED")
