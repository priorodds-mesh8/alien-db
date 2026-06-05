#!/usr/bin/env python3
"""Standalone test of prototype flow (no Gradio dep). Exercises chunks, local search, events, toy eval, synthesize stub."""
import json
import sys
import time
from pathlib import Path

root = Path(__file__).parent.parent
sys.path.insert(0, str(root))
sys.path.insert(0, str(root / "packages"))

from uap_corpus import write_event, new_run_id

CHUNKS_PATH = Path("data/chunks/nuforc-chunks.jsonl")

def load_chunks(limit=1000):
    if not CHUNKS_PATH.exists():
        return []
    recs = []
    with CHUNKS_PATH.open() as f:
        for i, line in enumerate(f):
            if i >= limit: break
            try:
                recs.append(json.loads(line))
            except:
                pass
    return recs

def tokenize(t): return set(t.lower().replace("\n"," ").split())

def local_search(chunks, query, shape="", has_abduction=False, top_k=5):
    qterms = tokenize(query)
    hits = []
    for r in chunks:
        md = r.get("metadata", {})
        if shape and (md.get("shape") or "").lower() != shape.lower(): continue
        if has_abduction and not md.get("possible_abduction"): continue
        text = r.get("chunk_text", "") + " " + str(md)
        score = sum(1 for w in qterms if w in text.lower())
        if score > 0 or not qterms:
            hits.append({**r, "_score": score})
    hits.sort(key=lambda x: x["_score"], reverse=True)
    return hits[:top_k]

def toy_fabrication_eval(synthesis, evidence):
    evidence_joined = " ".join(evidence).lower()
    fabricated = []
    for claim in ["implant", "hybrid", "government cover"]:
        if claim in synthesis.lower() and claim not in evidence_joined:
            fabricated.append(claim)
    total = max(3, len(synthesis.split(". ")))
    score = 1.0 - (len(fabricated) / total)
    return {"score": round(max(0.6, min(0.98, score)), 3), "fabricated": fabricated}

def main():
    chunks = load_chunks(10)
    print(f"Loaded {len(chunks)} chunks for test")

    run_id = new_run_id("test-proto")
    write_event(run_id, "rag.query.start", {"query": "test gray exam", "filters": {}})

    hits = local_search(chunks, "gray beings missing time", has_abduction=True, top_k=2)
    print(f"Search hits: {len(hits)}")

    evidence = [h.get("chunk_text","") for h in hits]
    synthesis = "Recurring: gray exam + missing time + telepathy. Cultural note: common in 80s+ media. Mundane alternatives possible."
    evalr = toy_fabrication_eval(synthesis, evidence)

    write_event(run_id, "tool.result", {"tool": "uap.search", "result_summary": f"{len(hits)} hits"})
    write_event(run_id, "synthesis.complete", {"eval_score": evalr["score"]})

    trace_file = Path("runs") / f"{run_id}.jsonl"
    print(f"Trace written to {trace_file}")
    print("Sample events:")
    for line in trace_file.read_text().strip().splitlines()[:3]:
        print("  ", json.loads(line)["kind"])

    print("Prototype flow test: OK (local search + events + eval)")

if __name__ == "__main__":
    main()
