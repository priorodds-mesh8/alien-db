# Real Embeddings, Pinecone, and How We Use the UAP Vector DB

This document explains exactly what changed for the 105 chunks, what embeddings are, how Pinecone enables semantic search, and the end-to-end usage of this vector database for UFO/UAP pattern research (per the approved plan).

## What Were the Embeddings Before?

- The 105 chunks (from 100 real NUFORC reports) were seeded into Pinecone ns=`nuforc-v0.1-proto` on the `alien-db-uap` index (dense, cosine, dim=1024).
- Previously the vectors were either:
  - Pseudo (hash-based placeholders from early demo code), or
  - From an "integrated" records API attempt (Pinecone server-side embedding with a different/unknown model, or un-normalized).
- Evidence: stored vectors had norm ~19 (not unit), search using the records `/.../search?inputs.text=...` endpoint returned HTTP 400 (incompatible with our plain dense index config).
- Result: metadata filters worked in some cases, but **no reliable semantic similarity**. Retrieval was closer to keyword or random.

We confirmed by fetching vectors, inspecting norms/distributions, and seeing the broken search path.

## What Are (Real) Embeddings?

An **embedding** is a dense vector of floats (here: 1024 dimensions) produced by a neural model (here: `intfloat/e5-large-v2`) that maps text into a high-dimensional space where **semantic similarity ≈ geometric proximity**.

- Similar meaning → high cosine similarity (dot product after L2 normalization).
- "Small gray beings with large black eyes performing medical examinations on a table" and a report describing "three small gray entities... subject on table... missing time 2 hours" will have vectors with cosine ~0.8+ even if they share few exact keywords.
- Dissimilar ("I saw a bright light in the sky that was probably Venus") will be far away (~0.2-0.4).
- We use **prefixes** for the e5 model:
  - Storage: `passage: <chunk_text>` (tells model "this is a document to be retrieved")
  - Query: `query: <user text>` (tells model "this is a search request")
- `normalize_embeddings=True` → unit vectors (norm ≈ 1.0). Pinecone cosine metric then = simple dot product.
- Why this model: 1024 dim matches our index exactly; strong on retrieval benchmarks; local, no per-query cost or extra key; open weights.

Embedder lives at `packages/uap_corpus/embedder.py` (lazy-loads SentenceTransformer only when needed; swappable later to Voyage/OpenAI/etc. by changing 3 functions).

## How Pinecone Stores and Searches Them Now

Index: `alien-db-uap` (serverless AWS us-east-1, dense 1024, cosine).

- **Upsert (seed time)**: 
  - `scripts/seed_uap.py --reset` (or without) loads the 105 chunk JSONL records.
  - `PineconeClient.upsert_chunks()` calls `embed_passages()` → gets 1024d vecs.
  - Then `upsert_vectors()` POSTs to `{host}/vectors/upsert`:
    ```json
    {"vectors": [
      {"id": "160452-c0", "values": [0.0369, -0.0506, ..., ~1024 floats norm=1], 
       "metadata": {"chunk_text": "Boardman Ohio. As we drove... triangle shaped craft...", "shape": "Triangle", "possible_abduction": false, "location": "...", "occurred": "...", ... }}
    ], "namespace": "nuforc-v0.1-proto"}
    ```
  - `chunk_text` + all filterable fields + light enrich (entities/effects as lists of str) live in metadata. No separate "payload" store needed.
- **Delete for clean re-seed**: `client.delete_namespace()` → POST `{host}/vectors/delete` with `{"deleteAll": true, "namespace": "..."}`.
- **Query (search time)**:
  - `client.search("small gray beings large black eyes medical exam", top_k=5, filters={"possible_abduction": {"$eq": true}, "shape": {"$eq": "Triangle"}})`
  - Inside: `qvec = embed_query(query)` → `POST {host}/query` with:
    ```json
    {"namespace": "...", "vector": [0.00x, ...], "topK": 5, "filter": {...}, "includeMetadata": true}
    ```
  - Pinecone computes cosine (dot of normalized), applies filter, returns top matches with their metadata (incl. the original `chunk_text`).
  - Returns: `[{"id": "...", "score": 0.89, "chunk_text": "...", "metadata": {shape, occurred, ...}}]`
- Hybrid = vector similarity (semantic) **AND** metadata filter (exact/structured). E.g., only abduction-flagged triangles that are semantically close to the gray-exam motif.
- Local fallback (no key): still token-overlap in `local_fallback_search` + same filters (for dev/offline).
- All via custom REST port (no official `pinecone-client` SDK) for minimal deps + exact control, modeled on the TS `mcp-memory` client.

Current stats after `--reset` + real seed: 105 vectors in the ns, all with norm=1.0, first values small floats typical of normalized e5 passage embeddings.

## How Exactly Are We Going to Use This Vector DB of UFO Sightings? (The RAG + Pattern System)

This is **not** a search engine for "find this one report". It is the retrieval layer for **glass-box, fabrication-resistant, motif/archetype discovery** over anecdotal public reports.

### The Full Pipeline (v0.1)

1. **Ingest** (one-time or incremental)
   - `download_nuforc.py` → HF `kcimc/NUFORC` (public) → normalized JSONL (id, narrative, occurred, location, shape, possible_abduction bool, missing_time/animals_reacted/etc flags, observer_count...).
   - `chunk_and_enrich.py` → recursive char chunks (~target size, light overlap) + light rule-based (or future real LLM structured JSON via xAI default) for `entities`, `effects`, `sequence`.
   - `seed_uap.py --reset` → embed passages + upsert (real vecs + metadata incl chunk_text).

2. **Query + Retrieve (semantic + hybrid)**
   - User (or UI or future agent): natural language query + optional filters.
     - Example queries from plan:
       - "small gray beings with large black eyes performing medical examinations on a table with missing time"
       - "missing time after highway encounter with bright light"
       - "silent black triangle hovering low over house no sound animals panicked"
   - `PineconeClient.search(...)` or Gradio "Analyze" → real e5 query vec + optional `{"possible_abduction": {"$eq": true}}` etc.
   - Returns top-k raw chunks (with full narrative text + structured meta + enrich) that are **semantically closest** in the embedding space, further narrowed by filters.
   - This is the "evidence pool". Everything downstream is strictly grounded in these strings.

3. **Synthesize (the heart of the plan prompt)**
   - Feed the retrieved chunks (as "Evidence: [1] id | shape=... | abduction=... | loc=...\n text...") + original query to LLM.
   - **Exact system prompt used** (from plan + wired in ui/app.py and prior artifacts):
     > "You are an objective researcher analyzing patterns in reported anomalous experiences. Here are the most semantically similar accounts. Identify recurring motifs, common sequences of events, variations in descriptions, potential clusters or archetypes, and any notable similarities or differences. Note possible cultural, psychological, or mundane explanations where relevant. Structure your output clearly. Always ground claims in the provided evidence."
   - LLM (xAI/Grok default via openai-compat; fallback Anthropic) outputs:
     - Recurring motifs (e.g. "Gray Being Medical Exam")
     - Common sequences (approach/hover/no-sound → close entity / beam / table → departure at extreme velocity → after-effects)
     - Variations (some with telepathy/implants, some only distant lights + animal reactions)
     - Archetypes/clusters
     - Explicit caveats: "data is anecdotal/unverified", "echoes known cultural narratives since 1980s (e.g. Hopkins, Jacobs, Strieber)", "mundane alternatives (drones, misID aircraft, sleep paralysis, hoaxes) remain possible for any individual case"
   - **No** free invention. The prompt + our later eval enforce grounding.

4. **Fabrication / Hallucination Eval (conservative, per handbook)**
   - Port of `agentic-sdr-demo` hallucination rubric (fabrication-only, not "is this true in reality").
   - Only flags:
     - Direct contradictions with the retrieved evidence pool, or
     - Very specific claims with zero support in the evidence (e.g. "named the being 'Zor' at 03:17" when no such detail anywhere in chunks).
   - Always appends: "anecdotal/unverified reports", "possible mundane/cultural".
   - Score (0-1) + list of flagged items surfaced in UI and trace.
   - This is what makes the system "glass-box" and defensible to skeptics.

5. **Motif Benchmark Scoring (Revenue Memory / AlertMedia style)**
   - Synthetic "known high-signal" archetype records in `packages/uap_corpus/fixtures/uap_benchmark.py`:
     - gray_medical_exam_missing_time
     - silent_triangle_hover_animal_reaction
     - disk_beam_livestock
   - For top retrieved hits, compute overlap/similarity scores against these.
   - Surfaces "this real chunk scored 0.95 on the silent-triangle motif benchmark".
   - Future: use for automated clustering, "how much does this new report resemble known archetypes", eval of retrieval quality.

6. **Full Trace (events JSONL)**
   - Every run: `rag.query.start` (query + filters), `tool.call` (name="uap.search_reports", arguments), `tool.result` (count, latency, source=pinecone), `synthesis.complete`, `eval.score`.
   - Written via `write_event` (modeled on mcp-memory/events).
   - `scripts/replay.py runs/xxx.jsonl` → human readable reconstruction, no LLM calls.
   - Source of truth for "what evidence was actually fed to the model on this date".

7. **UI (Gradio) + Future**
   - `ui/app.py`: textbox query, dropdown/checkbox filters, "Analyze patterns" → evidence markdown (raw chunks), synth output, summary (fab score + motifs + cost), full trace jsonl.
   - Local fallback when no Pinecone key (still useful for dev).
   - Cost meter, GLOBAL_METER.
   - Later (per plan): more sources (Blue Book/NARA via HF or OCR), reranker, clustering, continuous ingest, Next.js parity, Obsidian entity auto-create for strong archetypes.

### Why This Design? (The "Why" from the Original Plan)

- Anecdotal data is noisy, culturally contaminated, and easy to cherry-pick.
- Pure keyword search or LLM "summarize all UFO reports" → hallucinations + no provenance.
- Vector DB + RAG with **explicit evidence in prompt + conservative eval + traces** gives:
  - Reproducible, auditable "here is exactly the 5 chunks the model saw".
  - Ability to surface weak signals / recurring sequences that humans miss in 147k rows.
  - Built-in skepticism (mundane notes + "this may be cultural contamination").
  - Benchmarking against planted high-signal motifs (like Revenue Memory did for sales patterns).
- Pinecone choice: metadata filtering is excellent for hybrid (decade, shape, abduction flag, location geo later), serverless, fast cosine, integrated metadata+text return.
- Client embeddings (vs Pinecone hosted): full control of model/version, offline capability, reproducibility, no surprise model changes, easy to swap/eval different embedders.

### Current State (After This Change) + How to Use

- 105 chunks have **real** e5-large-v2 embeddings (norm=1, passage prefixed).
- `python scripts/seed_uap.py --ns nuforc-v0.1-proto --reset` to re-do after more chunks/enrich.
- `python ui/app.py` → enter motif queries above, toggle filters, Analyze. Watch the trace file update in `runs/`.
- `python scripts/replay.py runs/<latest>.jsonl`
- `python scripts/test_prototype_flow.py` (local path)
- To add more data: download more, chunk+enrich (add real LLM calls once keys solid), seed (can use same ns; it will add/overwrite by id).
- Obsidian: `alien database/artifacts/plan-v01.html` (the styled plan), v0.1 status, entity pages for surfaced archetypes (with #archetype #uap, caveats, links back to traces), vault indexer for LLM context.

### Next / Open (per PLAN + user)

- Valid keys (xAI preferred for inference; Anth for now hitting 401 in this env).
- Scale beyond 105 (more NUFORC + other corpora).
- Real LLM structured enrich in chunker (instead of light rules).
- Stronger eval (full port of hallucination.ts logic against raw chunk texts).
- UI button for "run benchmark suite", clustering viz, etc.
- Production: dedup, rerank (e.g. voyage or cross-encoder), namespaces per source/version, continuous ingest + webhooks.
- Legal/ethics: everything public-domain or fair-use research context; heavy caveats everywhere; no PII scraping.

All code changes are in git (or will be). Traces are the audit log. The vector DB is the semantic memory that lets the "objective researcher" LLM operate over the corpus without losing the "which reports?" thread.

See also: `CLAUDE.md`, `PLAN.md`, `packages/uap_corpus/embedder.py`, `pinecone_client.py`, `ui/app.py`, and the Obsidian artifacts.