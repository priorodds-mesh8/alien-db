# PLAN.md — alien-db v0.1

**Problem.** Public UAP/UFO/abduction report corpora are large, anecdotal, and hard to query for patterns without cherry-picking or losing provenance.

**Thesis.** A glass-box RAG over a properly chunked + enriched vector corpus (Pinecone integrated, rich metadata filters) + fabrication-only eval on every synthesis gives researchers and skeptics a traceable way to surface recurring motifs while explicitly surfacing limits and alternative explanations.

**v0.1 locked (user answers + revision):** NUFORC HF only (first 105 chunks), Gradio explorer first, **real client embeddings (e5-large-v2) + Pinecone dense vectors** (chunk_text + rich metadata in index, hybrid semantic+filter search), new ~/alien-db repo, artifacts (plan HTML etc) in Obsidian `alien database/artifacts/`.

**Status.** Proto (105 chunks + real e5 embeddings) complete. Full dataset pipeline added for the entirety:

- ~295,697 unique reports (deduped).
- ~21,179 chunks after light recursive chunking + rule enrich (actual; prior estimate was high).
- Streaming download / chunk (light rules forced for scale) / batched embed+seed (EMBEDDER_DEVICE=cpu recommended for reliability).
- Use dedicated ns "nuforc-full" (or "nuforc-v1") so proto 105 in v0.1-proto remains untouched.
- Commands in CLAUDE.md. Full embed+seed of 21k is CPU-heavy (~1-3+ hrs on Mac); monitor via the script prints.

See CLAUDE.md + EMBEDDINGS_AND_USAGE.md for exact commands and how the vector DB powers the RAG motif discovery loop.
