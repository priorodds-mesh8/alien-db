# alien-db

Glass-box RAG over public UAP/UFO sighting and abduction report corpora (starting with NUFORC).

v0.1 scope (locked): NUFORC HF only, Gradio explorer, Pinecone integrated (chunk_text + metadata, server-side embed like the AlertMedia Revenue Memory RAG in agentic-sdr-demo), full JSONL traces + fabrication-only eval.

See CLAUDE.md for commands and reuse notes. See plan.md (and the rendered HTML in Obsidian alien database/artifacts/plan-v01.html) for the full approved implementation plan, critical paths, verification steps, and architecture.

## Quickstart (prototype)
1. uv venv or python -m venv .venv && source .venv/bin/activate
2. pip install -r requirements.txt (or uv pip)
3. cp .env.example .env (add keys)
4. # sample
   python scripts/download_nuforc.py --limit 2000
   python scripts/chunk_and_enrich.py --input data/processed/nuforc-sample.jsonl --out data/chunks/nuforc-chunks.jsonl --enrich light
   EMBEDDER_DEVICE=cpu python scripts/seed_uap.py --ns nuforc-v0.1-proto --input data/chunks/nuforc-chunks.jsonl --reset
5. # full corpus (~148k reports -> 21k chunks)
   python scripts/download_nuforc.py --full
   python scripts/chunk_and_enrich.py --input data/processed/nuforc-full.jsonl --out data/chunks/nuforc-full-chunks.jsonl --enrich light
   EMBEDDER_DEVICE=cpu python scripts/seed_uap.py --ns nuforc-full --input data/chunks/nuforc-full-chunks.jsonl --reset --batch-size 128
6. python ui/app.py   # set PINECONE_NAMESPACE=nuforc-full (or edit .env) for full corpus

All synthesis output is traceable, evaluated for fabrication against raw retrieved chunks, and cost-metered.

## Status — v0.1 complete (closed out 2026-07)

Full corpus pipeline complete: ~147,891 unique NUFORC reports (deduped from ~591k raw HF rows) → 21,179 chunks → real e5-large-v2 embeddings in Pinecone ns `nuforc-full`. Proto 105 in `nuforc-v0.1-proto`. Live at https://alien-db-chi.vercel.app.

**Remediation pass (2026-07)** — analysis → fixes across integrity, deploy, robustness, all shipped, tested, and (for the integrity fixes) runtime-verified against live Pinecone:
- **Glass-box integrity:** floor-free claim-level fabrication eval; synthesis no longer emits hardcoded archetype prose (derived + `[STATIC]`-tagged disclaimer); case-robust shape filter (fixed a ~90% silent under-return on live data); all six boolean flags + `shape_lc` threaded into chunk metadata.
- **Deploy:** fixed the live HTTP 500 (Vercel was auto-installing torch/CUDA); static-only config.
- **Robustness:** Pinecone retry/backoff, resumable seed (`--resume`), real per-model cost metering, empty-query guard, shared Pydantic stage-boundary schema, enrich `--max-cost` ceiling.
- **Frontend a11y:** reduced-motion, dialog/focus-trap, fail-soft on data load.
- Tests: `.venv/bin/python scripts/test_{tier1_integrity,tier3_robustness,schema}.py` (48 checks, no keys needed).

**A hybrid-UI redesign (dense "SENTRY-style" explorer + Report Drawer) was scoped and deliberately dropped** — v0.1 keeps the existing Gradio research UI + the illustrative retro-arcade Motif Explorer. Consequences of that decision left as accepted limitations: the arcade runs on synthetic/illustrative data (labeled as such), per-report `url` stays the `https://nuforc.org/` placeholder, and the new `shape_lc`/flag metadata is live-verified but not backfilled into `nuforc-full` (a full re-seed is only worth doing when a feature consumes those fields).

<details><summary>Motif Explorer build history (Claude Design assets)</summary>
- Pixel-perfect to the new design: full CRT/arcade (scanlines, flicker, starfield, bezels, Press Start 2P + VT323), custom per-motif 8-bit invaders (bitmaps + bob/march + fire shot FX on click), big ROLL with live scanning animation (invaders + bar + count to 21179), GAME-OVER overlays for common/weird (semantic units + citations + why + "noise or artifact?" vote buttons), toy 2D semantic space plot, 8-bit WebAudio SFX (SND toggle), ticker, etc.
- 5 commons use our real counts (1247/892/1644/1483/723) + design's beautiful bitmaps + illustrative quotes. ROLL uses the design's rich ~30 rare "weird" clusters (perfect teaching examples).
- Launch the rebuilt UI: open `artifacts/motif-explorer/index.html` (the folder has index.html + motif-data.js + app.js; works directly in browser). Also synced to Obsidian artifacts.
- Gradio `ui/app.py` Motif section now promotes/links the polished demo while keeping live retrieval buttons.
- Real data note: the compute (when finished) will let us wire authentic quotes/IDs; current is the visual+interaction rebuild.
- Original handoff prompt + design screenshots preserved in `artifacts/motif-explorer/uploads/` and `screenshots/`.
</details>

## Pinecone Assistant (managed chat over the data)
In addition to the custom glass-box RAG in `ui/app.py`, you can build a managed **Pinecone Assistant** on the same NUFORC data:

```bash
# Small test (recommended first)
python scripts/build_pinecone_assistant.py --limit 200

# Or more
python scripts/build_pinecone_assistant.py --limit 2000 --name alien-db-uap
```

The script:
- Creates an assistant named `alien-db-uap` (with research-oriented instructions).
- Uploads full sighting reports (narrative + structured metadata for filtering on shape, possible_abduction, etc.).
- Uses `pc.assistants.upload_file` with byte streams + metadata (no temp files needed).

Then chat in the [Pinecone console](https://app.pinecone.io) (Assistants → your assistant) or programmatically:

```python
from pinecone import Pinecone
from pinecone_plugins.assistant.models.chat import Message

pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
resp = pc.assistants.chat(
    assistant_name="alien-db-uap",
    messages=[Message(role="user", content="What patterns appear in abduction reports involving small gray beings?")],
    filter={"possible_abduction": True}   # metadata filter
)
print(resp.message.content)
# Citations point back to the uploaded sighting files
```

**Tradeoffs vs custom RAG**:
- Pinecone Assistant: zero infra, built-in citations, easy filters, managed embeddings + LLM.
- Custom (current ui/app + seed): exact e5-large-v2 embeddings you chose, rich hybrid metadata filters at query time, full JSONL traces, fabrication-only eval, reproducible evidence pool, specific system prompt + local fallback.

Both can coexist on the same underlying data. The script above is a convenience for the managed path.

## Live Instance
- GitHub: https://github.com/priorodds-mesh8/alien-db (monorepo)
- **Live: https://alien-db-chi.vercel.app** — canonical production URL for this project.
  (The bare `alien-db.vercel.app` subdomain belongs to a different Vercel project and is not ours.)
  - Root (`/`): the exhaustive intro + links to Motif Explorer
  - `/motif-explorer`: the full rebuilt arcade UI from Claude Design assets (pixel invaders, ROLL, etc.)
- Static-only deploy: `vercel.json` (`installCommand` no-op, `cleanUrls`, rewrites/redirects) + `.vercelignore`
  excludes all Python surfaces so Vercel does not try to install torch/CUDA (that install phase was the
  cause of the earlier HTTP 500).

Deploys are connected to git pushes to `main`.
