#!/usr/bin/env python3
"""
Chunk narratives + optional LLM enrichment (entities, timeline, effects).

v0.1: pure-python recursive char chunker (no extra deps). Enrichment is pass-through or very light rule-based unless ANTHROPIC_API_KEY present (then structured JSON via Anthropic).

Usage:
  python scripts/chunk_and_enrich.py --in data/processed/nuforc-sample.jsonl --out data/chunks/nuforc-chunks.jsonl --limit 500

Output: one chunk record per line with id, source_report_id, chunk_text, metadata (shape, possible_abduction, location, ...), entities[], effects[], seq[] (enriched or []).
"""
import argparse
import json
import os
import re
from pathlib import Path
from typing import List, Dict, Any

from dotenv import load_dotenv
load_dotenv()  # Load local .env if present (project-specific keys)

try:
    import anthropic
except ImportError:
    anthropic = None

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

DEFAULT_IN = Path("data/processed/nuforc-sample.jsonl")
DEFAULT_OUT = Path("data/chunks/nuforc-chunks.jsonl")

XAI_API_KEY = os.getenv("XAI_API_KEY")
ANTHROPIC_KEY = os.getenv("ANTHROPIC_API_KEY")

def chunk_text(text: str, max_chars: int = 2200, overlap: int = 300) -> List[str]:
    """Simple recursive-ish chunker on paragraphs/sentences."""
    if not text:
        return []
    paras = re.split(r"\n{2,}", text.strip())
    chunks: List[str] = []
    buf = ""
    for p in paras:
        p = p.strip()
        if not p:
            continue
        if len(buf) + len(p) + 1 > max_chars and buf:
            chunks.append(buf.strip())
            # overlap
            tail = buf[-overlap:] if len(buf) > overlap else buf
            buf = tail + "\n\n" + p
        else:
            buf = (buf + "\n\n" + p).strip()
    if buf:
        chunks.append(buf.strip())
    # final split if a chunk is still too long
    final = []
    for c in chunks:
        if len(c) <= max_chars:
            final.append(c)
        else:
            # hard split
            for i in range(0, len(c), max_chars - overlap):
                final.append(c[i:i+max_chars])
    return final

def light_enrich(narrative: str) -> Dict[str, Any]:
    """Zero-dep placeholder. Real version calls Anthropic for structured extract per pasted 'Metadata enrichment'.
    Enhanced with more patterns for better demo output on real samples.
    """
    entities = []
    effects = []
    seq = []
    low = narrative.lower()
    if "gray" in low or "grey" in low:
        entities.append({"type": "being", "desc": "small gray being with large black eyes"})
    if "missing time" in low or "time loss" in low or "unaccounted" in low:
        effects.append("missing time")
        seq.append("missing time reported after close approach or encounter")
    if "medical" in low or "examination" in low or "table" in low or "probed" in low:
        seq.append("subject placed on table / examined or probed")
    if "telepath" in low or "mind" in low or "communicated" in low:
        entities.append({"type": "communication", "desc": "telepathic or direct mind communication"})
    if "scar" in low or "implant" in low or "mark" in low:
        effects.append("physical mark / implant / scar")
    if "beam" in low or "light" in low and "scanned" in low:
        seq.append("beam of light scanned subject or area")
    if "triangle" in low or "triangular" in low:
        entities.append({"type": "craft", "desc": "triangular or triangle-shaped craft"})
    if "silent" in low or "no sound" in low:
        effects.append("silent operation / no sonic boom")
    if "animal" in low and ("react" in low or "crazy" in low or "hid" in low or "panic" in low):
        effects.append("animal reactions (distress, hiding, freezing)")
    return {"entities": entities, "effects": effects, "sequence": seq}

def real_enrich(narrative: str) -> Dict[str, Any]:
    """Prefer xAI (Grok) for structured JSON extraction of entities, effects, sequence.
    Falls back to Anthropic (Claude) if no XAI key.
    Uses the spirit of the pasted context prompt for objective analysis.
    """
    if XAI_API_KEY and OpenAI:
        try:
            client = OpenAI(
                api_key=XAI_API_KEY,
                base_url="https://api.x.ai/v1",
            )
            system = "You are an objective researcher extracting structured facts from anomalous experience reports. Output ONLY valid JSON with keys: entities (array of {type, desc}), effects (array of strings), sequence (array of event strings in order). Be conservative; only extract what is explicitly described. Do not invent."
            user = f"Report narrative:\n{narrative}\n\nExtract the structured data as JSON."
            resp = client.chat.completions.create(
                model="grok-beta",
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user}
                ],
                response_format={"type": "json_object"},
                max_tokens=800,
            )
            text = resp.choices[0].message.content if resp.choices else "{}"
            start = text.find("{")
            end = text.rfind("}") + 1
            if start != -1 and end > start:
                data = json.loads(text[start:end])
                return {
                    "entities": data.get("entities", []),
                    "effects": data.get("effects", []),
                    "sequence": data.get("sequence", []),
                }
        except Exception as e:
            print(f"  xAI/Grok enrich failed, falling back: {e}")

    if ANTHROPIC_KEY and anthropic:
        try:
            client = anthropic.Anthropic(api_key=ANTHROPIC_KEY)
            system = "You are an objective researcher extracting structured facts from anomalous experience reports. Output ONLY valid JSON with keys: entities (array of {type, desc}), effects (array of strings), sequence (array of event strings in order). Be conservative; only extract what is explicitly described. Do not invent."
            user = f"Report narrative:\n{narrative}\n\nExtract the structured data as JSON."
            resp = client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=800,
                system=system,
                messages=[{"role": "user", "content": user}],
            )
            text = resp.content[0].text if resp.content else "{}"
            start = text.find("{")
            end = text.rfind("}") + 1
            if start != -1 and end > start:
                data = json.loads(text[start:end])
                return {
                    "entities": data.get("entities", []),
                    "effects": data.get("effects", []),
                    "sequence": data.get("sequence", []),
                }
        except Exception as e:
            print(f"  Anthropic enrich failed, falling back: {e}")

    return light_enrich(narrative)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", dest="input_path", type=Path, default=DEFAULT_IN)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--limit", type=int, default=0, help="Max reports to process (0 = all)")
    ap.add_argument("--chunk-chars", type=int, default=2200)
    ap.add_argument("--enrich", choices=["light", "llm", "auto"], default="auto",
                    help="Enrichment mode. 'light' = rules only (recommended for full 148k+). 'llm' = always call xAI/Anthropic. 'auto' = llm only for small inputs.")
    args = ap.parse_args()

    args.out.parent.mkdir(parents=True, exist_ok=True)

    # Decide enrichment strategy up front for large runs
    use_llm = False
    if args.enrich == "llm":
        use_llm = True
    elif args.enrich == "light":
        use_llm = False
    else:  # auto
        # For full dataset we refuse expensive LLM unless user forces --enrich llm
        if args.limit == 0 or args.limit > 10000:
            print("Large/full run detected (limit=0 or >10k). Forcing light enrichment to avoid massive LLM cost/time.")
            print("Use --enrich llm only if you really want (and have budget + patience).")
            use_llm = False
        else:
            use_llm = bool(XAI_API_KEY or ANTHROPIC_KEY)

    print(f"Streaming chunk + enrich from {args.input_path} (chunk~{args.chunk_chars}, enrich={'light' if not use_llm else 'LLM'}) ...")

    limit = args.limit if args.limit > 0 else None
    out_count = 0
    seen = set()  # simple dedup on normalized chunk text
    processed_reports = 0

    with args.input_path.open() as fin, args.out.open("w") as fout:
        for i, line in enumerate(fin):
            if limit and processed_reports >= limit:
                break
            if not line.strip():
                continue
            try:
                r = json.loads(line)
            except Exception:
                continue

            processed_reports += 1
            narr = r.get("narrative") or ""
            chunks = chunk_text(narr, max_chars=args.chunk_chars)

            enrich = real_enrich(narr) if use_llm else light_enrich(narr)

            for ci, ch in enumerate(chunks):
                norm = ch[:200].lower().replace(" ", "")
                if norm in seen:
                    continue
                seen.add(norm)

                chunk_rec = {
                    "chunk_id": f"{r['id']}-c{ci}",
                    "source_report_id": r["id"],
                    "source": r.get("source"),
                    "chunk_text": ch,
                    "metadata": {
                        "occurred": r.get("occurred"),
                        "location": r.get("location"),
                        "shape": r.get("shape"),
                        "possible_abduction": r.get("possible_abduction"),
                        "observer_count": r.get("observer_count"),
                    },
                    "entities": enrich.get("entities", []),
                    "effects": enrich.get("effects", []),
                    "sequence": enrich.get("sequence", []),
                }
                fout.write(json.dumps(chunk_rec, ensure_ascii=False) + "\n")
                out_count += 1

            if processed_reports % 2000 == 0:
                print(f"  processed {processed_reports} reports -> {out_count} chunks so far...")

    print(f"Wrote {out_count} chunks from {processed_reports} reports -> {args.out}")
    print("Note: For full corpus use --enrich light (default now for large). LLM enrichment per report is very expensive at scale.")

if __name__ == "__main__":
    main()
