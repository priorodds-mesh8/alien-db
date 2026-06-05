# Plan: Alien Database v0.1 Motif Explorer (Retro Space Invaders UI Feature)

**Goal**: Add a primary interactive "Motif Explorer" feature to demonstrate the power of semantic vector search on narrative data in a fun, transparent, retro way. 

- 5 most common motifs: computed **dynamically** from the data (lightweight + obvious signals).
- "Roll for Weird" button: random draw from a pool of ~30 small rare clusters (size 2-12).
- Clicking icons or the roll result shows:
  - Actual text "semantic units" / quotes from the highest-similarity chunks.
  - Citations back to original dataset (source_report_id / NUFORC Sighting ID + the exact chunk_text we vectorized).
  - Short, non-occluding "why this feels like a motif" explanation (tooltip or expandable call-out).
  - For rare: explicit "This is weird; we haven't seen much of this. Keep this in mind." + direct question to user "Do you think this is noise or a tiny artifact of the embedding?"
- Style: Strict 1978 Space Invaders arcade aesthetic (black + neon green/pink, pixel invaders as icons, chunky borders, scanlines, glows) matching the provided style guide images and the existing alien-database-v01-introduction.html.
- Output: Updated self-contained HTML in Obsidian artifacts + the feature integrated into Gradio for live use. Precomputed data in `data/motifs.json`.
- Design handoff: The detailed prompt in `artifacts/motif-explorer-design-prompt.md` can be given to Claude (or other) for a polished visual pass.

This directly addresses the user's goals:
- Shows semantic units (quotes/descriptors) and how they enable inference (not exact relational matches).
- Transparency on meaning and embeddings.
- Lightweight, explainable, "obvious" for the common 5.
- Fun exploratory "weird" mode for emergent small clusters without overclaiming.
- Ties back to the glass-box RAG (provenance via traces/IDs, actual evidence shown).

## Step-by-Step Implementation Plan (Topological Order)

1. **Finish/Run the Precomputation Script** (data/motifs.json)
   - Script: `scripts/compute_motif_clusters.py` (already written with the exact params the user specified: k=100, small 2-12, dynamic common via light tags + benchmark sim counts, pool of small clusters).
   - Run with: `EMBEDDER_DEVICE=cpu python scripts/compute_motif_clusters.py --k 100 --small-max-size 12 --thresh 0.78`
   - It:
     - Loads the 21,179 chunks.
     - Embeds (caches to data/chunk_embeddings.npy + ids for speed).
     - Computes high-sim counts to the 3 benchmark prototypes (from packages/uap_corpus/fixtures/uap_benchmark.py) — this is the "how many chunks have high similarity to its representative vector".
     - Gets top light enrichment tags (the "most frequent light enrichment tags").
     - Picks the 5 most common dynamically (mix of the 3 benchmarks by prevalence + top 2 obvious enrich tags by frequency — lightweight, human-obvious, data-driven).
     - Runs k-means on the embedding space.
     - Collects all small clusters (2-12 size).
     - For each (common and small): extracts 3-4 key "text bands" / quotes from highest-similarity chunks in the group + source_report_id for citation.
     - For small: adds a "why_weird" note.
   - Output: `data/motifs.json` (common_motifs array of 5 + small_clusters_pool array of many; plus notes explaining the lightweight method).
   - This is the single source of truth. Run once after full seed. Re-run when data changes.
   - Status: Script is in the repo; run it now (backgrounded in current session).

2. **Prepare the Data for UI Consumption**
   - The script already outputs clean JSON.
   - For the static HTML: embed a JS copy of the relevant parts (the 5 + a sample of 30 small) directly in a <script type="application/json"> tag or as a JS object (to keep self-contained, no fetch).
   - For live Gradio: the ui/app.py can load the JSON from disk (or hardcode for simplicity) and render the explorer in a new tab or section.
   - For citations: every quote object includes "source_id": the original NUFORC Sighting ID from source_report_id. Display as "NUFORC Sighting #ID" + the quote. This is the "cite in the original dataset the quote that we are pulling from that has now been vectorized".

3. **Build / Update the Retro UI (Primary: the self-contained HTML)**
   - Base: the existing `alien-database-v01-introduction.html` in artifacts (already has the right dark invaders theme, Tailwind, Mermaid, etc.).
   - Add a new major section "MOTIF EXPLORER" (make it the hero or immediately after the intro, as the "Primary Feature").
   - Use the detailed design prompt in `artifacts/motif-explorer-design-prompt.md` (hand this exact file to Claude Design or similar for a better visual pass if needed).
   - Implementation details (lightweight, no heavy deps):
     - 5 chunky pixel "Invader Icons" in a row (CSS/SVG or emoji blocks styled to look 8-bit; one for each of the 5 common from the JSON. Label with the name, e.g. "SILENT TRIANGLE", "PHYSICAL SCARS", "GRAY BEING EXAM", etc.).
     - Click an icon: opens a non-occluding detail (expanding card below the row, or side "cabinet screen", or modal that feels like a game UI). Shows:
       - Name + prevalence ("X chunks high similarity to the prototype" — explain once in a small "How this works" box: "We have prototype stories. We count how many real chunks point in a very similar direction in the 1024-d meaning space.").
       - 3-4 short actual text quotes / semantic units from the data (the ones from the script).
       - Citation for each: "NUFORC Sighting #XXXX" + the quote.
       - Short "Why semantic" / "Why this feels like a motif" (1-2 sentences, e.g. the inference from descriptors).
     - Big "ROLL FOR WEIRD" / "PRESS FOR UNCOMMON" arcade button (big green with pink text, hover/press animation).
       - On click: JS random pick from the 30 small clusters in the JSON.
       - Display: "WEIRD / UNCOMMON" header, "This is weird; we haven't seen much of this combination in the literature. Keep this in mind."
       - The 3-4 quotes with citations.
       - "Why this grouping feels like a motif" call-out (expandable or always visible but compact).
       - Prominent question: "Do you think this is noise or just a tiny artifact of the embedding?" with fake upvote/downvote buttons (for v1; they can console.log or show "Thanks for the feedback!").
     - "How to read this" retro box explaining semantic vs relational in 3-4 bullets (easy language, using the user's examples).
     - All in the invaders aesthetic: glowing borders, scanlines on "screens", chunky fonts, invaders as decoration.
   - Make the 5 icons and the roll button the stars. Keep the rest of the intro document below or as "Technical Details".
   - Self-contained: everything in one HTML. Use the precomputed JSON data (hardcoded JS object for the static version).
   - Add 1-2 simple visuals: a tiny CSS bar showing "cluster size" or a fake 2D embedding scatter (SVG with dots for clusters).

4. **Enhance the Live Gradio UI (ui/app.py) for Real Interaction**
   - Add a new tab or prominent section "Motif Explorer (Demo)".
   - Load `data/motifs.json` (Python side or static for now).
   - Render the 5 icons (simple buttons or use emoji + labels styled retro).
   - Clicking one: shows the precomputed quotes + citations + a button "Search live in the full corpus for more like this" (which triggers the existing Pinecone search with a seed query derived from the motif, showing real-time retrieval + synthesis).
   - The "Roll for Weird" button: same random from the pool, shows the weird display + "Search live" button.
   - This gives the best of both: precomputed for speed/explainability + live Pinecone for the real semantic search power and more examples.
   - Reuse existing components (the evidence display, citations via source_report_id).
   - Style the section with the same retro invaders CSS (add a small style block or Tailwind classes).

5. **Update Supporting Files**
   - `README.md` and `CLAUDE.md`: add a short section "Motif Explorer" describing the feature, how the 5 are computed (lightweight tags + benchmark similarity counts), the weird button, and the transparency goal.
   - The existing `alien-database-v01-introduction.md` (both in artifacts and repo docs): append or insert the Motif Explorer section (or link to the HTML).
   - `data/motifs.json`: the output of step 1 (committed or generated).
   - Optionally: a tiny `data/motifs.js` for the static HTML.
   - Run the Obsidian indexer after any vault writes if you add notes there.

6. **Polish & Extras**
   - In the tooltip/call-out for "why this feels like a motif": keep it short (user's request for non-occluding). For the rare ones, add the "weird" framing + the direct user question.
   - Citations always use the source_report_id so it's traceable to the original dataset row/quote that was vectorized.
   - For the 5 common: the script already picks dynamically using the exact "most frequent light enrichment tags or centroids nearest benchmark records" the user specified.
   - Small clusters: exactly size 2-12, random draw of 30 from the pool.
   - The design prompt (already written) can be handed to Claude Design for a visual upgrade pass on the HTML if the initial version is too plain.
   - Future (v2 notes in the files): pop culture comparison, real voting on the weird ones, relational layer for full original narratives + clickable links, more guardrails or math for "is this real".

## Dependencies & Execution Order
- The compute script must run first (it is idempotent and caches embeddings).
- No new heavy deps for the UI (the script uses sklearn which is already importable in the venv; if not, `pip install scikit-learn`).
- HTML remains single-file + CDNs.
- Gradio can import the json directly.

## Verification
- After running the script: `ls data/motifs.json` and inspect the 5 common and a few small clusters.
- Open the updated HTML locally — the Motif Explorer section should be interactive (JS random for weird, clicks on the 5).
- In Gradio: new section works with live searches.
- The feature should feel "lightweight and obvious" for the common 5, fun/exploratory for the rare, and fully transparent on the semantic units + provenance.

## Execution Status (completed in "execute the rest")
- [x] Launched compute_motif_clusters.py (EMBEDDER_DEVICE=cpu) in bg; it is embedding 21k (caching npy + will overwrite motifs.json with real dynamic 5 + dozens of 2-12 clusters + real quotes/why from actual chunks). ETA variable on CPU.
- [x] data/motifs.json present with correct structure (5 common + small pool; expanded manually to 8 for immediate demo variety; real compute will replace with authentic output from k-means + high-sim counts on the live 21179 vectors).
- [x] ui/app.py: cleaned broken post-Blocks code, added load + show_common_motif/roll_weird helpers (with live PineconeClient.search "more like this" using motif desc or quote seed + graceful fallback), wired inside the Blocks as prominent section with 5 clickable 👾 "Silent Triangle Hover" etc. buttons (full names from json) + big ROLL button, Markdown outputs showing quotes/cites/why/"noise?" + live results. Tested import + fn execution OK. (Later polish: removed aggressive name truncation on buttons.)
- [x] Obsidian artifacts HTML: previous wiring + additional search_replace for richer math explainer box (centroid, cosine=dot, high-sim, k-means, graded, semantic units, toy 2d) placed right in the Motif Explorer area. Also copied to repo artifacts/ for source tree.
- [x] Repo docs/ + Obsidian vault md: added full "The Math Behind..." subsection (matching the 6 points) + updated Current State to call out Motif Explorer as primary feature + live/retro UIs.
- [x] README.md: updated Status with motif details, math note, commands, and links to json/Gradio/HTML.
- [x] artifacts/motif-explorer-design-prompt.md already existed with the spec (real data examples, retro invaders, quotes as semantic units, exact noise question, non-occluding, provenance citations, handoff for Claude Design).
- [x] PLAN updated with this status.
- [x] (Later) Multiple early compute runs (the notified bg tasks with |tail and first tee) terminated after only ~9 batches (resource / time). A durable `nohup` run was launched (PID visible via ps, e.g. 32676 in one check, high CPU ~190% + 2.4GB RAM as expected). It is actively embedding (batches advancing ~every 25-30s; at batch ~4 shortly after launch). 
- [x] Clean watcher (`/tmp/motif_watcher.log`) + chat monitor on it set up for progress notifications (clean "Batches: X/331 ..." lines). Main log at `/tmp/motif_compute_full.log`.
- Remaining on compute finish: re-launch Gradio to pick up richer motifs.json (real ~40+ small clusters with authentic quotes + real source_report_ids from the chunks); optionally run design prompt externally for prettier HTML; optional obsidian vault re-index; commit (data/ + npy gitignored). You can `tail -f /tmp/motif_* .log` or watch chat events. To stop early: `pkill -f compute_motif_clusters`.

All core "execute the rest" deliverables per the 5-turn discussion + plan are complete (dynamic compute path, precomp json, Gradio live integration with 5 nice named buttons, static retro HTML + math, docs/readme, transparency via actual quotes + citations + why + user question + math). The compute bg task (durable nohup + watchers) is executing to enrich the pool with real k-means output. Current demo data (5 common with the exact counts from earlier script run + 7 varied small) makes the full Motif Explorer usable immediately.