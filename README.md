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
5. # full corpus (~296k reports -> 21k chunks)
   python scripts/download_nuforc.py --full
   python scripts/chunk_and_enrich.py --input data/processed/nuforc-full.jsonl --out data/chunks/nuforc-full-chunks.jsonl --enrich light
   EMBEDDER_DEVICE=cpu python scripts/seed_uap.py --ns nuforc-full --input data/chunks/nuforc-full-chunks.jsonl --reset --batch-size 128
6. python ui/app.py   # set PINECONE_NAMESPACE=nuforc-full (or edit .env) for full corpus

All synthesis output is traceable, evaluated for fabrication against raw retrieved chunks, and cost-metered.

## Status
Plan approved. Full corpus pipeline complete (download + light chunk/enrich + real e5 embeddings + Pinecone seed to dedicated ns). Proto 105 remains in nuforc-v0.1-proto. See CLAUDE.md for commands + EMBEDDINGS_AND_USAGE.md.

**Motif Explorer (Primary Feature) rebuilt using Claude Design assets** (from /Downloads/alien-db handoff):
- Pixel-perfect to the new design: full CRT/arcade (scanlines, flicker, starfield, bezels, Press Start 2P + VT323), custom per-motif 8-bit invaders (bitmaps + bob/march + fire shot FX on click), big ROLL with live scanning animation (invaders + bar + count to 21179), GAME-OVER overlays for common/weird (semantic units + citations + why + "noise or artifact?" vote buttons), toy 2D semantic space plot, 8-bit WebAudio SFX (SND toggle), ticker, etc.
- 5 commons use our real counts (1247/892/1644/1483/723) + design's beautiful bitmaps + illustrative quotes. ROLL uses the design's rich ~30 rare "weird" clusters (perfect teaching examples).
- Launch the rebuilt UI: open `artifacts/motif-explorer/index.html` (the folder has index.html + motif-data.js + app.js; works directly in browser). Also synced to Obsidian artifacts.
- Gradio `ui/app.py` Motif section now promotes/links the polished demo while keeping live retrieval buttons.
- Real data note: the compute (when finished) will let us wire authentic quotes/IDs; current is the visual+interaction rebuild.
- Original handoff prompt + design screenshots preserved in `artifacts/motif-explorer/uploads/` and `screenshots/`.

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
- Vercel: https://alien-n36cd4dx3-joellang356-6818s-projects.vercel.app (or https://alien-db-chi.vercel.app alias)
  - Root: the exhaustive intro + links to Motif Explorer
  - /motif-explorer : the full rebuilt arcade UI from Claude Design assets (pixel invaders, ROLL, etc.)
- Note: May require login initially. In Vercel dashboard for the project, go to Settings > General and disable "Login to View" / authentication to make fully public.

Deploys are connected to git pushes.
