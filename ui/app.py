#!/usr/bin/env python3
"""
Gradio v0.1 explorer for Alien Database (UAP RAG prototype).

- Pinecone (real e5-large-v2 1024d client embeddings + vector search) or local token fallback
- Metadata hybrid filters (shape, possible_abduction)
- Synthesizer (xAI default per plan, fallback Anthropic) using exact "objective researcher" prompt
- Fabrication-only eval (conservative: contradictions or zero-evidence specifics only)
- Full JSONL events trace (rag.query, tool.call uap.search_reports, synthesis, eval.score)
- Motif benchmark scores (synthetic high-signal archetypes)
- Direct + dense. Glass box: retrieved raw chunks always visible; everything traceable.

Run: python ui/app.py  (first run with Pinecone key will download ~1.3G e5 model on first semantic query)
"""
import json
import os
import sys
import time
from pathlib import Path
from typing import List, Dict, Any

import gradio as gr
from dotenv import load_dotenv

# Make local packages importable
root = Path(__file__).parent.parent
sys.path.insert(0, str(root))
sys.path.insert(0, str(root / "packages"))

load_dotenv()  # project .env first (XAI preferred, PINECONE_*)

from uap_corpus import (
    PineconeClient, write_event, new_run_id, GLOBAL_METER,
    get_benchmark_records, UAP_BENCHMARK_RECORDS,
    fabrication_eval, build_shape_filter,
)

XAI_API_KEY = os.getenv("XAI_API_KEY")
ANTHROPIC_KEY = os.getenv("ANTHROPIC_API_KEY")

CHUNKS_PATH = Path(os.getenv("UAP_LOCAL_CHUNKS", "data/chunks/nuforc-full-demo.jsonl"))  # 5k demo for better local fallback; proto or full-demo; pinecone path used when key present

def load_chunks(limit: int = 1000) -> List[Dict[str, Any]]:
    if not CHUNKS_PATH.exists():
        return []
    recs = []
    with CHUNKS_PATH.open() as f:
        for line in f:
            if len(recs) >= limit:
                break
            try:
                recs.append(json.loads(line))
            except:
                pass
    return recs

CHUNKS = load_chunks()

def tokenize(t: str) -> set:
    return set(t.lower().replace("\n", " ").split())

def local_search(query: str, shape: str = "", has_abduction: bool = False, top_k: int = 6) -> List[Dict]:
    qterms = tokenize(query)
    hits = []
    for r in CHUNKS:
        md = r.get("metadata", {})
        if shape and (md.get("shape") or "").lower() != shape.lower():
            continue
        if has_abduction and not md.get("possible_abduction"):
            continue
        text = r.get("chunk_text", "") + " " + str(md)
        score = sum(1 for w in qterms if w in text.lower())
        if score > 0 or not qterms:
            hits.append({**r, "_score": score})
    hits.sort(key=lambda x: x["_score"], reverse=True)
    return hits[:top_k]

def _local_synthesize(query: str, chunks: List[Dict]) -> str:
    """Evidence-only fallback synthesis. No LLM required. Grounded strictly in the retrieved chunks."""
    if not chunks:
        return "No strong matching reports in the current sample. Try broadening the query or removing filters."

    shapes = {}
    locations = {}
    all_text = []
    for c in chunks:
        md = c.get("metadata", {}) or {}
        s = (md.get("shape") or "Unknown").strip() or "Unknown"
        shapes[s] = shapes.get(s, 0) + 1
        loc = md.get("location") or "?"
        # simplify location to country/region-ish
        if "," in loc:
            loc = loc.split(",")[-1].strip()
        locations[loc] = locations.get(loc, 0) + 1
        all_text.append((c.get("chunk_text") or "").lower())

    top_shapes = ", ".join(f"{s}×{n}" for s, n in sorted(shapes.items(), key=lambda x: -x[1])[:4])
    top_locs = ", ".join(f"{l}×{n}" for l, n in sorted(locations.items(), key=lambda x: -x[1])[:4])

    # naive recurring terms (very lightweight)
    from collections import Counter
    words = Counter()
    for t in all_text:
        for w in t.split():
            if len(w) >= 5 and w.isalpha() and w not in {"about", "there", "their", "would", "could", "after", "before", "being", "other", "these", "those", "which", "where", "while"}:
                words[w] += 1
    common_terms = ", ".join(w for w, _ in words.most_common(7)) or "none prominent"

    # very short excerpts for key motifs
    excerpts = []
    for c in chunks[:3]:
        txt = (c.get("chunk_text") or "")[:180].replace("\n", " ").strip()
        sid = (c.get("metadata", {}) or {}).get("source_report_id") or c.get("source_report_id") or c.get("id") or "?"
        excerpts.append(f"• \"{txt}...\" — #{sid}")

    # Pattern notes DERIVED from these chunks' enrichment fields (not a canned paragraph).
    # Aggregate the entities/effects/sequence the enricher actually extracted from the retrieved
    # reports, so the description reflects THIS result set rather than a hardcoded archetype.
    from collections import Counter as _Counter
    ent_c, eff_c, seq_c = _Counter(), _Counter(), _Counter()
    for c in chunks:
        for e in (c.get("entities") or []):
            desc = e.get("desc") if isinstance(e, dict) else str(e)
            if desc:
                ent_c[desc] += 1
        for ef in (c.get("effects") or []):
            if ef:
                eff_c[str(ef)] += 1
        for sq in (c.get("sequence") or []):
            if sq:
                seq_c[str(sq)] += 1

    def _top(counter, n=4):
        return "; ".join(f"{k} (×{v})" for k, v in counter.most_common(n))

    derived_bits = []
    if ent_c:
        derived_bits.append(f"**Entities described:** {_top(ent_c)}")
    if eff_c:
        derived_bits.append(f"**Reported effects:** {_top(eff_c)}")
    if seq_c:
        derived_bits.append(f"**Event sequence elements:** {_top(seq_c)}")
    if derived_bits:
        pattern_notes = "**Pattern notes (derived from these " + str(len(chunks)) + " chunks):**\n" + "\n".join(derived_bits)
    else:
        pattern_notes = ("**Pattern notes:** The retrieved chunks carry no structured "
                         "entity/effect tags from the light enricher, so no motif summary is "
                         "asserted here — read the excerpts above directly.")

    # The disclaimer below is a fixed methodological caveat, NOT an analysis of these chunks.
    # It is tagged [STATIC] so the fabrication evaluator does not score it as (un)grounded and so
    # readers can see it is boilerplate rather than a claim about the retrieved evidence.
    static_disclaimer = (
        "[STATIC] **Critical limits & mundane alternatives (fixed methodological note, not derived "
        "from these chunks):** These are anecdotal, unverified public reports collected over decades. "
        "Abduction-narrative motifs have circulated widely in books, media, and hypnosis sessions for "
        "decades, creating real risk of cultural contamination, suggestion, confabulation, or false "
        "memory. Sleep paralysis, hypnagogic hallucination, hoaxes, misidentification of aircraft/drones, "
        "and psychological factors remain plausible for any individual case. No physical evidence, "
        "independent corroboration, or causal conclusion can be drawn from these texts alone; the data "
        "only surfaces recurring *reported* motifs for further (skeptical) investigation."
    )

    return (
        f"**Local evidence-based analysis** (no LLM used — keys missing/invalid/no credits. "
        f"Strictly from the {len(chunks)} retrieved chunks only):\n\n"
        f"**Shapes in results:** {top_shapes}\n"
        f"**Locations:** {top_locs}\n"
        f"**Recurring terms:** {common_terms}\n\n"
        "Key excerpts from top matches:\n" + "\n".join(excerpts) + "\n\n"
        + pattern_notes + "\n\n"
        + static_disclaimer
    )


def synthesize(query: str, chunks: List[Dict]) -> str:
    if not chunks:
        return "No strong matching reports in the current sample. Try broadening the query or removing filters."

    evidence_text = "\n\n".join(
        f"[{i+1}] {c.get('chunk_id', c.get('id','?'))} | shape={c.get('metadata',{}).get('shape','?')} | abduction={c.get('metadata',{}).get('possible_abduction')} | loc={c.get('metadata',{}).get('location','?')}\n{c.get('chunk_text','')[:420]}..."
        for i, c in enumerate(chunks)
    )

    if not (XAI_API_KEY or ANTHROPIC_KEY):
        return _local_synthesize(query, chunks)

    # Prefer xAI/Grok, fallback to Anthropic. Uses the exact prompt style from the approved plan.
    try:
        if XAI_API_KEY:
            from openai import OpenAI
            client = OpenAI(
                api_key=XAI_API_KEY,
                base_url="https://api.x.ai/v1",
            )
            system_prompt = "You are an objective researcher analyzing patterns in reported anomalous experiences. Here are the most semantically similar accounts. Identify recurring motifs, common sequences of events, variations in descriptions, potential clusters or archetypes, and any notable similarities or differences. Note possible cultural, psychological, or mundane explanations where relevant. Structure your output clearly. Always ground claims in the provided evidence."
            user_prompt = f"Query: {query}\n\nAccounts:\n{evidence_text}\n\nAnalyze as instructed."
            for model in ["grok-4.3", "grok-4.20-0309-reasoning", "grok-4.20-0309-non-reasoning", "grok-4.20-multi-agent-0309"]:
                try:
                    resp = client.chat.completions.create(
                        model=model,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt}
                        ],
                        max_tokens=1500,
                    )
                    if resp.choices:
                        u = getattr(resp, "usage", None)
                        GLOBAL_METER.log_call(
                            model,
                            getattr(u, "prompt_tokens", 0) or 0,
                            getattr(u, "completion_tokens", 0) or 0,
                        )  # cost priced from the per-model table (Grok is NOT free)
                        return resp.choices[0].message.content
                except Exception:
                    continue
            # xai failed (bad key / no credits / bad model), try anth below if key
        if ANTHROPIC_KEY:
            import anthropic
            client = anthropic.Anthropic(api_key=ANTHROPIC_KEY)
            system_prompt = "You are an objective researcher analyzing patterns in reported anomalous experiences. Here are the most semantically similar accounts. Identify recurring motifs, common sequences of events, variations in descriptions, potential clusters or archetypes, and any notable similarities or differences. Note possible cultural, psychological, or mundane explanations where relevant. Structure your output clearly. Always ground claims in the provided evidence."
            user_prompt = f"Query: {query}\n\nAccounts:\n{evidence_text}\n\nAnalyze as instructed."
            resp = client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=1500,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}]
            )
            u = getattr(resp, "usage", None)
            GLOBAL_METER.log_call(
                "claude-3-haiku-20240307",
                getattr(u, "input_tokens", 0) or 0,
                getattr(u, "output_tokens", 0) or 0,
            )
            return resp.content[0].text if resp.content else "No response from model."
        return _local_synthesize(query, chunks)
    except Exception as e:
        # Always fall back to useful local analysis instead of the old static canned text
        local = _local_synthesize(query, chunks)
        return f"LLM synthesis unavailable (error: {str(e)[:160]}).\n\n{local}"

def run_analysis(query: str, shape_filter: str, abduction_only: bool):
    t0 = time.time()
    run_id = new_run_id("uap-analysis")

    # Write start event
    write_event(run_id, "rag.query.start", {
        "query": query,
        "filters": {"shape": shape_filter, "abduction_only": abduction_only},
    })

    # Use Pinecone client (falls back internally if no key)
    client = PineconeClient.from_env()
    filters = {}
    # Case-robust shape filter: dropdown may emit lowercase while NUFORC metadata is Title-case;
    # Pinecone $eq is case-sensitive, so build a $in over casing variants (see build_shape_filter).
    filters.update(build_shape_filter(shape_filter))
    if abduction_only:
        filters["possible_abduction"] = {"$eq": True}

    if client:
        hits = client.search(query, top_k=5, filters=filters or None)
        search_source = "pinecone"
    else:
        hits = local_search(query, shape_filter, abduction_only, top_k=5)
        # normalize local hits to have chunk_text / metadata
        for h in hits:
            if "chunk_text" not in h:
                h["chunk_text"] = h.get("narrative", "")
            if "metadata" not in h:
                h["metadata"] = {k: h.get(k) for k in ["shape", "possible_abduction", "location", "occurred"] if k in h}
        search_source = "local_fallback"

    # Benchmark motif scoring (like Revenue Memory in agentic-sdr-demo)
    benchmarks = get_benchmark_records()
    motif_scores = []
    for h in hits[:3]:
        h_text = (h.get("chunk_text", "") + " " + str(h.get("metadata", {}))).lower()
        best_score = 0
        best_motif = ""
        for b in benchmarks:
            b_text = b.get("chunk_text", "").lower()
            overlap = sum(1 for w in h_text.split() if w in b_text and len(w) > 3)
            score = min(0.95, 0.2 + overlap * 0.08)
            if score > best_score:
                best_score = score
                best_motif = b.get("motif", "")
        motif_scores.append({"motif": best_motif, "score": round(best_score, 2)})

    # Emit tool.call like event
    write_event(run_id, "tool.call", {
        "tool": "uap.search_reports",
        "args": {"query": query, "filters": filters},
        "call_id": f"search-{int(t0)}",
    })

    evidence_chunks = [h.get("chunk_text", "") for h in hits]
    # synthesize() self-meters real token usage into GLOBAL_METER when an LLM is used
    # (priced per-model); the local fallback genuinely costs $0.
    synthesis = synthesize(query, hits)
    eval_res = fabrication_eval(synthesis, evidence_chunks)

    # Emit tool.result
    write_event(run_id, "tool.result", {
        "tool": "uap.search_reports",
        "call_id": f"search-{int(t0)}",
        "result_summary": f"Retrieved {len(hits)} chunks (source={search_source})",
        "latency_ms": int((time.time() - t0) * 1000),
        "cost_usd": 0.0,
    })

    # Emit synthesis
    write_event(run_id, "synthesis.complete", {
        "synthesis_preview": synthesis[:200] + "...",
        "eval_score": eval_res["score"],
    })

    # Emit eval
    write_event(run_id, "eval.score", {
        "score": eval_res["score"],
        "fabricated_count": len(eval_res.get("fabricated", [])),
        "notes": eval_res.get("notes", ""),
    })

    trace = {
        "run_id": run_id,
        "t": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "query": query,
        "filters": {"shape": shape_filter, "abduction_only": abduction_only},
        "search_source": search_source,
        "retrieved": [{"id": h.get("id") or h.get("chunk_id"), "score": h.get("score") or h.get("_score"), "metadata": h.get("metadata", {})} for h in hits],
        "motif_scores": motif_scores,
        "synthesis": synthesis,
        "eval": eval_res,
        "latency_ms": int((time.time() - t0) * 1000),
        "cost_usd": GLOBAL_METER.total_cost(),
    }
    trace_json = json.dumps(trace, indent=2)

    # Also append full events file content for "show trace"
    events_file = Path("runs") / f"{run_id}.jsonl"
    if events_file.exists():
        trace_json = events_file.read_text()  # show the real events log

    # Human readable summary
    cost = GLOBAL_METER.total_cost()
    motif_str = ", ".join([f"{m['motif']}:{m['score']}" for m in motif_scores if m['motif']]) or "none"
    summary = f"Found {len(hits)} matching chunks (via {search_source}). Fabrication score: {eval_res['score']}. Motif scores: {motif_str}. Cost so far: ${cost:.4f}. "
    if eval_res["fabricated"]:
        summary += f"Flagged: {', '.join(eval_res['fabricated'])}"
    else:
        summary += "No obvious fabrications against the retrieved evidence pool."

    # Evidence display using chunk_text
    evidence_md = "\n\n".join(
        f"**[{h.get('id') or h.get('chunk_id','?')}]** score={h.get('score') or h.get('_score','?')} | {h.get('metadata',{}).get('shape','?')} @ {h.get('metadata',{}).get('location','?')}\n{h.get('chunk_text', h.get('narrative',''))[:320]}..."
        for h in hits
    )

    return (
        evidence_md,
        synthesis,
        summary,
        trace_json
    )


# --- Motif Explorer support (Primary Feature) ---
import json as json_mod
MOTIFS_JSON = root / "data" / "motifs.json"
MOTIF_DATA = {}
if MOTIFS_JSON.exists():
    with open(MOTIFS_JSON) as f:
        MOTIF_DATA = json_mod.load(f)
else:
    MOTIF_DATA = {"common_motifs": [], "small_clusters_pool": [], "notes": {}}

def _format_motif(m: Dict) -> str:
    out = f"**{m.get('name', 'Motif')}**"
    cnt = m.get('count')
    if cnt:
        out += f"  —  {cnt} chunks high-sim or frequent"
    out += "\n\n"
    out += "**Semantic units (actual quotes from the chunks that were vectorized into this motif's neighborhood):**\n"
    for q in m.get("quotes", [])[:4]:
        sid = q.get("source_id") or q.get("source_report_id", "?")
        out += f"- \"{q.get('text','')}\" — NUFORC Sighting #{sid}\n"
    desc = m.get("description") or m.get("why_weird") or ""
    if desc:
        out += f"\n**Why this grouping feels like a motif:** {desc}\n"
    out += "\n*These quotes are the 'semantic units' — short phrases whose embeddings point in a similar direction in 1024-d space even if wording varies. This is how we do inference beyond exact tags/keywords (vs a relational DB row match).*"
    return out

def show_common_motif(idx: int) -> str:
    cms = MOTIF_DATA.get("common_motifs", [])
    if not cms:
        return "No motifs.json found. Run `EMBEDDER_DEVICE=cpu python scripts/compute_motif_clusters.py` first to generate the dynamic 5 + small pool from the 21,179 chunks."
    idx = max(0, min(idx, len(cms)-1))
    m = cms[idx]
    base = _format_motif(m)
    # Try live retrieval for "more like this" using the motif description/name as query against nuforc-full
    live = ""
    try:
        client = PineconeClient.from_env()
        qtext = m.get("description") or m.get("name", "uap motif")
        if client:
            hits = client.search(qtext, top_k=3, filters=None)
            live = "\n\n**Live semantic search in full Pinecone nuforc-full (more like this motif):**\n"
            for h in hits:
                txt = (h.get("chunk_text") or "")[:160].replace("\n"," ")
                sid = h.get("metadata", {}).get("source_report_id", h.get("id", "?"))
                live += f"- \"{txt}...\" — #{sid} (score ~{h.get('score',0):.3f})\n"
        else:
            live = "\n\n(Live Pinecone not available in this env; using local fallback would go here. Paste the motif name into the top analyzer for retrieval.)"
    except Exception as e:
        live = f"\n\n(Live search error or no key: {str(e)[:80]})"
    return base + live

def roll_weird() -> str:
    pool = MOTIF_DATA.get("small_clusters_pool", [])
    if not pool:
        return "No small_clusters_pool in motifs.json. Run the compute script (k-means on embeddings produces the 2-12 size emergent clusters)."
    import random
    r = random.choice(pool)
    base = f"**WEIRD / UNCOMMON — cluster size {r.get('size', '?')} (k-means id {r.get('cluster_id', '?')})**\n\n"
    base += '"This is weird; we haven\'t seen much of this combination in the literature. Keep this in mind."\n\n'
    base += "**Key quotes (semantic units / text bands from highest-similarity chunks in this small cluster):**\n"
    for q in r.get("quotes", [])[:4]:
        sid = q.get("source_id") or q.get("source_report_id", "?")
        base += f"- \"{q.get('text','')}\" — NUFORC Sighting #{sid}\n"
    why = r.get("why_weird", "Tight semantic neighborhood in the embedding space (unexpected co-occurrence of descriptors).")
    base += f"\n**WHY THIS GROUPING FEELS LIKE A MOTIF:** {why}\n"
    base += "\n**Do you think this is noise or just a tiny artifact of the embedding?** (👍 / 👎 — real persistent voting + aggregation is v2)"
    # live more
    live = ""
    try:
        client = PineconeClient.from_env()
        # derive a query from the quotes or why
        qseed = " ".join([q.get("text","") for q in r.get("quotes",[])[:2]]) or "uncommon uap cluster"
        if client:
            hits = client.search(qseed[:300], top_k=2)
            live = "\n\n**Live 'more like this' from Pinecone (same embedding space):**\n"
            for h in hits:
                txt = (h.get("chunk_text") or "")[:140].replace("\n"," ")
                sid = h.get("metadata", {}).get("source_report_id", "?")
                live += f"- \"{txt}...\" — #{sid}\n"
    except Exception:
        pass
    return base + live

with gr.Blocks(title="Alien Database — v0.1 Explorer") as demo:
    gr.Markdown("# Alien Database — v0.1 (Glass-Box UAP RAG prototype)\n**21,179 NUFORC chunks** (full deduplicated corpus) • **Real e5-large-v2 embeddings** in Pinecone (1024d cosine) + hybrid filters • Local evidence-based synthesis when LLM keys unavailable/invalid/no credits • fabrication-aware eval • motif benchmarks • replayable JSONL traces\n\nSemantic search is now live against the full corpus: similar meaning (not just keywords) surfaces via vector cosine. See CLAUDE.md + plan HTML in Obsidian for usage and the exact RAG flow. LLM synthesis requires a working XAI_API_KEY (with credits) or ANTHROPIC_API_KEY.")
    with gr.Row():
        q = gr.Textbox(label="Semantic query", value="small gray beings large black eyes medical examination missing time", lines=2)
        shape = gr.Dropdown(["", "Triangle", "Light", "Disk", "Circle", "Sphere", "Fireball", "Oval"], label="Shape filter (NUFORC Title-case)", value="")
        abd = gr.Checkbox(label="Possible abduction only", value=True)
    run_btn = gr.Button("Analyze patterns (retrieve + synthesize + eval)", variant="primary")

    with gr.Row():
        evidence = gr.Markdown(label="Retrieved evidence (raw chunks)")
        synth = gr.Markdown(label="Synthesizer output (grounded)")
    summary_box = gr.Textbox(label="Eval summary")
    trace_box = gr.Code(label="Full JSONL events trace (replayable)", language="json")

    run_btn.click(run_analysis, [q, shape, abd], [evidence, synth, summary_box, trace_box])

    gr.Markdown("**Note:** Full 21,179-chunk corpus with real e5-large-v2 client embeddings is live in Pinecone (nuforc-full ns). When XAI/ Anthropic keys are missing, invalid, or have no credits, the app falls back to a fully local evidence-based summary (no LLM). Traces in runs/*.jsonl. Local token-overlap fallback only used if no Pinecone key. See CLAUDE.md for commands.")

    # === MOTIF EXPLORER (Primary Feature) integrated here ===
    gr.Markdown("---\n## 🎮 MOTIF EXPLORER — Primary Feature (v0.1)\n**5 most common motifs** computed *dynamically* from the 21,179 real chunk embeddings (mix of light rule-based enrichment tag frequency + count of chunks with high cosine similarity to the 3 benchmark prototype vectors). **Roll for Weird**: random from the pool of small k-means clusters (size 2–12 only). Shows the actual semantic unit quotes (the text that got vectorized) + source citations + why callout + the direct 'noise or embedding artifact?' question. Live 'more like this' retrieval against the full Pinecone index when available.\n\nThis is the glass-box demo of semantics: you see the exact phrases whose 1024-d vectors landed near each other or near the archetype rep vector. Not relational exact match — graded similarity in meaning space.")
    gr.Markdown("**Click a motif icon** for its precomputed semantic units (quotes from the actual vectorized chunks) + citations + live search results for 'more like this' in the full corpus.")
    with gr.Row():
        common_out = gr.Markdown(label="Common Motif Detail (precomputed quotes + why + live Pinecone matches)")
    # 5 buttons for the common motifs (names from the json at startup)
    cms = MOTIF_DATA.get("common_motifs", [])
    with gr.Row():
        for i in range(min(5, len(cms))):
            nm = cms[i].get("name", f"Motif {i}")
            b = gr.Button(f"👾 {nm}", scale=1)
            # use default arg to capture current i
            b.click(lambda idx=i: show_common_motif(idx), outputs=common_out)

    roll_weird_btn = gr.Button("🎲 ROLL FOR WEIRD (random draw from small 2-12 clusters — emergent/uncommon combos)", variant="primary")
    weird_out = gr.Markdown(label="Weird Cluster + Quotes + Why + Noise Question + Live")
    roll_weird_btn.click(roll_weird, outputs=weird_out)

    gr.Markdown("**How the 5 common are chosen (lightweight & obvious, no black box):** frequency of the simple tags the chunker adds (e.g. physical mark, telepathic) + how many of the 21k chunks have cos sim >~0.78 to one of our 3 hand-curated high-signal prototype stories (gray medical, silent triangle, disk beam). The small clusters are pure k-means in the embedding space; we keep only the tiny ones (2-12 members) as 'weird emergent'. Every quote links back to the exact NUFORC ID of the report it came from.\n\n**Polished arcade UI (Claude Design rebuild):** The full retro experience with pixel invaders, scanning ROLL, overlays, sounds, plot etc. is at `artifacts/motif-explorer/index.html` (open the folder). Current Gradio buttons use the live corpus for 'more like this'. Re-run compute for the real full rare pool in the demo data file.")

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860, share=False)
