# CLAUDE.md — alien-db (UAP / Alien Database RAG)

Glass-box vector RAG for public UAP/UFO/abduction reports. Follows the exact Agentic SDR methodology from the handbook (fabrication-only eval, JSONL traces, MCP-style tools, cost ceilings, dense prose).

## Project
- Location: ~/alien-db (new independent git repo, sibling to ~/agentic-sdr-demo)
- v0.1: NUFORC HF only (105 chunks), Gradio explorer UI, **real client embeddings** (intfloat/e5-large-v2 1024d normalized via embedder.py) + Pinecone dense vector index (cosine) with chunk_text in metadata. Hybrid semantic + filters. Exactly reuses mcp-memory patterns + handbook eval.
- Obsidian thinking layer: alien database/ (plans, entities, artifacts). Never bulk code or raw reports here.

## Key Commands (working prototype first)
- `cd ~/alien-db && python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt gradio python-dotenv anthropic sentence-transformers tqdm`
- Small sample: `python scripts/download_nuforc.py --limit 2000`
- **Full dataset (~147,891 unique reports)**: `python scripts/download_nuforc.py --full`
- Chunk (light rules only for full — LLM per-report is too expensive): 
  `python scripts/chunk_and_enrich.py --input data/processed/nuforc-full.jsonl --out data/chunks/nuforc-full-chunks.jsonl --enrich light`
- Seed full with real embeddings (new ns, streaming batches): 
  `EMBEDDER_DEVICE=cpu python scripts/seed_uap.py --ns nuforc-full --input data/chunks/nuforc-full-chunks.jsonl --reset --batch-size 128`
  (MPS can be slow/hang on first encode for bulk; cpu is reliable. ~21k chunks (not 300k) took ~1-3+ hrs on 202x Mac CPU in testing — leave running. Progress prints every ~2k chunks.)
- Proto sample seed (105): `python scripts/seed_uap.py --ns nuforc-v0.1-proto --input data/chunks/nuforc-chunks.jsonl --reset`
- `python ui/app.py` — Gradio (semantic query ... now works against full or proto depending on .env PINECONE_NAMESPACE or client.ns override)
- `python scripts/build_pinecone_assistant.py --limit 200` — Create a managed Pinecone Assistant (uploads reports + metadata; chat in console or via pc.assistants.chat). See README for details + tradeoffs vs custom RAG.
- `python scripts/replay.py runs/<run-id>.jsonl`
- `python scripts/test_prototype_flow.py` (local only)
- After substantive work: `python ~/Documents/ObsidianVault/scripts/index-vault.py` then read latest sessions/index/*.html (HTML preferred for context)
- Motif Explorer (primary feature): `EMBEDDER_DEVICE=cpu python scripts/compute_motif_clusters.py --k 100 --small-max-size 12` (populates data/motifs.json from real 21k embeddings + k-means + bench sims). Then `python ui/app.py` and use the Motif section (or open artifacts HTML). The 5 common + roll weird show semantic units (quotes) + citations + live retrieval + math. Re-run after any chunk changes.

## Reuse (port with comments)
- Pinecone client patterns + metadata+chunk_text: ~/agentic-sdr-demo/packages/mcp-memory/src/pinecone.ts (now explicit vectors path)
- Fabrication rubric + grounding: ~/agentic-sdr-demo/packages/agents/src/eval/hallucination.ts (conservative contradictions only)
- Events, cost-meter, benchmark motif style from agentic-sdr-demo (Revenue Memory etc.)
- Full glass-box patterns from the agentic-sdr-demo web + RAG work
- Embedder choice (e5-large-v2 + prefixes) for strong retrieval on 1024d index (swappable later)

## Rules
- Working code over scaffolding. No placeholder comments.
- Direct + dense prose (no summaries of what you just did).
- Every synthesis must note data limits + possible mundane/cultural explanations.
- Traces (JSONL) are source of truth. Eval (fabrication-only against raw chunks) must pass.
- Artifact HTMLs go first to external ~/Alien Database - RAG/artifacts/ then indexed in Obsidian (plan-v01.html already done).
- Root CLAUDE.md + dense PLAN/DECISIONS/README in git; Obsidian for thinking + wiki entities + session indexes.

## First milestone (per approved plan)
Full prototype loop (download → chunk/enrich → **real embeddings + Pinecone vector seed** → Gradio query with semantic example → real vector+filter retrieval → xAI synth grounded in evidence + fab eval + complete replayable trace) + artifacts in Obsidian.

See PLAN.md (and its HTML) for full verification checklist and paths. Current focus after this: more data, better enrich (real LLM), benchmarks vs motifs, Obsidian entity pages for surfaced archetypes.
