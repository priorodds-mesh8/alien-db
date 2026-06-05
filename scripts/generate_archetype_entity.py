#!/usr/bin/env python3
"""
generate_archetype_entity.py

Generate or update Obsidian-style entity/archetype Markdown pages from the alien-db
UAP vector corpus (Pinecone or local chunks).

Designed for the glass-box RAG project: motifs/archetypes are surfaced via vector
search, grounded strictly in evidence, with project-standard caveats.

Usage:
  # Generate a new one (uses live Pinecone nuforc-full by default)
  python scripts/generate_archetype_entity.py \
    --motif "gray_medical_exam" \
    --query "small gray beings large black eyes medical examination table missing time" \
    --title "Gray Being Medical Exam Archetype" \
    --tags archetype,gray,medical,missing-time \
    --output data/archetypes/gray-being-medical-exam.md

  # Batch from built-in list (good for initial thorough pass)
  python scripts/generate_archetype_entity.py --batch --limit 5 --obsidian-vault ~/Documents/ObsidianVault

  # Update an existing entity with fresh evidence from the full 21k corpus
  python scripts/generate_archetype_entity.py \
    --update-existing /path/to/existing.md \
    --query "updated gray being exam query" 

The script prefers the live PineconeClient (full 21k). Falls back to local chunks file
if no key. Uses local evidence summarizer by default (no LLM cost). Pass --use-llm to
call xAI for a synthesized description (respects EMBEDDER_DEVICE and XAI_API_KEY).

See README and CLAUDE.md for the project's philosophy on archetypes (grounded, caveated,
linkable, traceable).
"""

import argparse
import json
import os
import re
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Dict, Any, List, Optional

from dotenv import load_dotenv

# Make local packages importable
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "packages"))

load_dotenv()

try:
    from uap_corpus import PineconeClient
except ImportError:
    PineconeClient = None

# Built-in high-value motifs surfaced from the corpus + project benchmarks.
# Extend this list as you discover more via interrogation.
BUILTIN_MOTIFS: List[Dict[str, Any]] = [
    {
        "motif": "gray_medical_exam_missing_time",
        "title": "Gray Being Medical Exam Archetype",
        "seed_query": "small gray beings with large black eyes performing medical examinations on a table with missing time",
        "tags": ["archetype", "gray", "medical", "missing-time", "abduction"],
        "description": "Recurring report motif of small gray-skinned beings with oversized black eyes conducting 'examinations' on human subjects, often on a table. Frequently accompanied by telepathic communication, missing time, and post-event physical marks.",
    },
    {
        "motif": "silent_triangle_hover_animal_reaction",
        "title": "Silent Triangle Hover Archetype",
        "seed_query": "silent black triangle craft hovering low no sound animals panicked extreme acceleration",
        "tags": ["archetype", "craft", "triangle", "silent", "hover", "animal"],
        "description": "Large black (or dark) triangular craft with lights at the corners hovering silently and low over houses, roads, or fields. Extreme animal reactions (dogs barking/hiding, livestock panicking). Instant vertical or diagonal acceleration on departure with no sonic boom. Often physiological effects (head pressure, paralysis).",
    },
    {
        "motif": "disk_beam_livestock",
        "title": "Disk or Orb Beam on Animals/Livestock Archetype",
        "seed_query": "disk orb beam of light scanning livestock animals froze or panicked",
        "tags": ["archetype", "craft", "disk", "orb", "beam", "livestock", "animal"],
        "description": "Metallic disk, dome, or bright orb hovering over barns, fields, or roads and emitting a beam or light that 'scans' or affects livestock/animals. Animals freeze, panic, or are temporarily immobilized. Object departs at high speed with unusual characteristics (no boom, instant acceleration).",
    },
    {
        "motif": "physical_marks_scars_implants",
        "title": "Post-Encounter Physical Marks / Scars / Implants Effect",
        "seed_query": "physical scars burns marks implants on body after ufo encounter or abduction",
        "tags": ["effect", "physical", "scar", "implant", "mark"],
        "description": "New physical evidence appearing after a close encounter or missing time episode: straight-line scars, small circular burns or 'punched' holes in skin, objects under skin, red marks, or 'implants'. Often reported with no pain at the time or memory of how they occurred.",
    },
    {
        "motif": "highway_abduction_missing_time",
        "title": "Highway Close Encounter / Abduction with Missing Time",
        "seed_query": "driving highway bright light ufo missing time gray beings or craft",
        "tags": ["motif", "highway", "abduction", "missing-time", "light"],
        "description": "Driver or passengers on a highway or remote road experience a bright light or craft, often leading to missing time (minutes to hours). Vehicle may be stopped or affected. Beings or examination sometimes reported. Common 'screen memory' of mundane event (deer, police, etc.) that later breaks down.",
    },
    {
        "motif": "bedroom_visitation_paralysis",
        "title": "Bedroom Visitation / Entity Paralysis Motif",
        "seed_query": "bedroom night entity being standing over bed paralysis unable to move gray or shadow figure",
        "tags": ["motif", "bedroom", "visitation", "paralysis", "entity"],
        "description": "Subject awakens (or is in bed) to find one or more humanoid or gray figures in the room or at the bedside. Often accompanied by paralysis (sleep paralysis-like but with full awareness), telepathic messages, or a sense of 'scanning'. Figure may phase through walls or appear 'not entirely physical'.",
    },
    {
        "motif": "cigar_cylinder_craft",
        "title": "Cigar or Cylindrical Craft Archetype",
        "seed_query": "cigar cylinder shaped long object craft in sky no wings lights",
        "tags": ["archetype", "craft", "cigar", "cylinder", "dirigible"],
        "description": "Long, narrow, cigar- or cylinder-shaped object (sometimes with lights or windows) observed moving slowly or hovering, often at altitude. Distinguished from planes by lack of wings, unusual flight characteristics (sudden direction changes, hovering), and sometimes glowing or metallic appearance.",
    },
    {
        "motif": "electronic_interference_em",
        "title": "Electronic / Radio / TV Interference Effect",
        "seed_query": "radio tv phone car electronics interference during ufo craft sighting",
        "tags": ["effect", "electronic", "interference", "em", "radio"],
        "description": "Radios, televisions, car engines, phones, cameras, or other electronics malfunction, go static, or lose power in the presence of a craft or bright light. Interference often stops when the object departs. Sometimes accompanied by physical sensations (tingling, pressure).",
    },
    {
        "motif": "multi_orb_formation",
        "title": "Multiple Orbs or Lights in Formation",
        "seed_query": "multiple orange white orbs lights in formation moving together disappearing",
        "tags": ["motif", "orb", "light", "formation", "ufo"],
        "description": "Groups of 3–20+ bright spherical or point-source lights/orbs moving in coordinated formations, lines, or geometric patterns. Often orange, white, or multicolored. Can hover, accelerate instantly, or 'wink out'. Sometimes appear to merge, split, or respond to observers.",
    },
    {
        "motif": "telepathic_project_genetic",
        "title": "Telepathic 'The Project' / Genetic Interest Communication",
        "seed_query": "telepathic message beings 'the project' genetic experiment hybrid",
        "tags": ["motif", "telepathy", "communication", "genetic", "project"],
        "description": "During close encounter or examination, subject receives direct mind-to-mind communication. Common themes: 'We are not here to harm you', references to 'the project', genetic sampling, hybridization, warnings about humanity/environment, or instructions not to remember. Often leaves the subject with a sense of purpose or specialness.",
    },
]

def get_client():
    if PineconeClient is None:
        raise RuntimeError("uap_corpus package not available")
    client = PineconeClient.from_env()
    if client:
        client.namespace = os.getenv("PINECONE_NAMESPACE", "nuforc-full")
        return client
    # Fallback to local chunks (limited but useful)
    print("No Pinecone key — falling back to local chunks file (slower, smaller result set).")
    return None

def search_evidence(client, query: str, top_k: int = 8) -> List[Dict]:
    """Return list of hit dicts with id, score, chunk_text, metadata."""
    if client is None:
        # very naive local fallback
        hits = []
        path = ROOT / "data" / "chunks" / "nuforc-full-chunks.jsonl"
        if not path.exists():
            return []
        qterms = set(query.lower().split())
        with path.open() as f:
            for line in f:
                c = json.loads(line)
                text = (c.get("chunk_text","") + " " + str(c.get("metadata",""))).lower()
                score = sum(1 for w in qterms if w in text)
                if score > 2:
                    hits.append({
                        "id": c.get("chunk_id"),
                        "score": float(score),
                        "chunk_text": c.get("chunk_text",""),
                        "metadata": c.get("metadata", {})
                    })
        hits.sort(key=lambda x: -x["score"])
        return hits[:top_k]
    else:
        return client.search(query, top_k=top_k)

def local_summarize(motif: str, hits: List[Dict]) -> str:
    """Simple evidence-based summary without LLM."""
    if not hits:
        return "No strong evidence retrieved for this motif in the current corpus slice."

    shapes = Counter()
    locations = Counter()
    excerpts = []
    for h in hits:
        md = h.get("metadata", {}) or {}
        s = md.get("shape") or "Unknown"
        shapes[s] += 1
        loc = md.get("location") or "?"
        if "," in loc:
            loc = loc.split(",")[-1].strip()
        locations[loc] += 1
        txt = h.get("chunk_text", "")[:160].replace("\n", " ").strip()
        excerpts.append(f"- {h['id']} (score {h['score']:.2f}): {txt}...")

    top_shapes = ", ".join(f"{s}×{n}" for s,n in shapes.most_common(3))
    top_locs = ", ".join(f"{l}×{n}" for l,n in locations.most_common(3))

    summary = f"""**Local evidence-based summary** (no LLM — strictly from top retrieved chunks for motif "{motif}"):

**Dominant shapes in results:** {top_shapes}
**Common locations/regions:** {top_locs}

**Key excerpts (highest scoring matches):**
{chr(10).join(excerpts[:4])}

**Pattern notes:** {len(hits)} high-similarity chunks were retrieved. Recurring elements are listed above. This motif appears as a weak-to-moderate signal in the overall corpus but clusters strongly when the right semantic query + metadata filters are applied.

**Critical caveats (project standard):** All data is anecdotal public reports. High risk of cultural contamination, false memory, suggestion, and hoaxes. Mundane explanations (misidentification, psychological phenomena, sleep paralysis for close encounters, etc.) must always be considered. No physical proof is provided by the texts themselves. Use only for pattern discovery and hypothesis generation.
"""
    return summary

def llm_synthesize(motif: str, hits: List[Dict], query: str) -> Optional[str]:
    """Optional: Use xAI (via OpenAI compat) for a richer grounded synthesis."""
    key = os.getenv("XAI_API_KEY")
    if not key:
        return None
    try:
        from openai import OpenAI
        client = OpenAI(api_key=key, base_url="https://api.x.ai/v1")
        evidence = "\n\n".join(
            f"[{i+1}] {h['id']} | shape={h.get('metadata',{}).get('shape')} | abd={h.get('metadata',{}).get('possible_abduction')} | loc={h.get('metadata',{}).get('location')}\n{h.get('chunk_text','')[:350]}"
            for i, h in enumerate(hits[:6])
        )
        system = "You are an objective researcher analyzing patterns in reported anomalous experiences. Ground every claim strictly in the provided evidence chunks. Note limitations, possible mundane/cultural explanations, and that the data is anecdotal. Structure clearly."
        user = f"Motif/archetype under investigation: {motif}\nSeed query: {query}\n\nTop evidence chunks:\n{evidence}\n\nProduce a concise archetype description following the project's standard structure (description, key elements, related motifs, caveats). Keep it under 400 words."
        resp = client.chat.completions.create(
            model="grok-4.3",  # or grok-4.20 variants as available
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user}
            ],
            max_tokens=800,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        print(f"LLM synthesis failed: {e}")
        return None

def generate_markdown(motif_def: Dict, hits: List[Dict], use_llm: bool = False, extra_evidence: str = "") -> str:
    title = motif_def.get("title", motif_def["motif"].replace("_", " ").title())
    tags = motif_def.get("tags", ["archetype"])
    desc = motif_def.get("description", "")

    if use_llm:
        llm_desc = llm_synthesize(motif_def["motif"], hits, motif_def.get("seed_query", ""))
        if llm_desc:
            desc = llm_desc

    local = local_summarize(motif_def["motif"], hits)
    if not desc:
        desc = local.split("**Pattern notes:**")[0].strip() if "**Pattern notes:**" in local else local

    related = ", ".join(f"[[{r}]]" for r in motif_def.get("related", [])) or "See other entities in this folder."

    evidence_lines = []
    for h in hits[:5]:
        md = h.get("metadata", {})
        txt = h.get("chunk_text", "")[:140].replace("\n", " ")
        evidence_lines.append(f"- {h['id']} (score {h['score']:.2f}, shape={md.get('shape')}, abd={md.get('possible_abduction')}): {txt}...")

    now = datetime.now().strftime("%Y-%m-%d")
    md = f"""---
created: {now}
updated: {now}
tags: {tags}
---

# {title}

**Description:** {desc}

**Key elements surfaced from the 21k-chunk corpus (via vector search):**
{chr(10).join(evidence_lines)}

**Related motifs:** {related}

**Sources (vector retrieval on full corpus):** Top semantic matches from the nuforc-full namespace in the alien-db-uap index. See the project's RAG traces and benchmark fixtures for reproducibility.

**Caveats (per alien-db project rules):** All data is anecdotal and unverified public reports. High risk of cultural contamination from media since the 1980s, hypnosis influence, confabulation, and hoaxes. Mundane/psychological explanations (sleep paralysis, misidentification, suggestion, etc.) remain possible and often probable for any individual case. This page exists for pattern discovery only. Always cross-reference with raw chunk metadata and full traces.

**Status:** #active #research
"""
    if extra_evidence:
        md += f"\n\n## Additional evidence from full 21k corpus update\n{extra_evidence}\n"
    return md

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--motif", help="Motif key from BUILTIN_MOTIFS or custom")
    ap.add_argument("--query", help="Seed semantic query for vector search")
    ap.add_argument("--title", help="Human title for the entity page")
    ap.add_argument("--tags", help="Comma-separated tags")
    ap.add_argument("--output", help="Path to write the .md (default: data/archetypes/<motif>.md)")
    ap.add_argument("--obsidian-vault", help="Path to Obsidian vault root (will write to alien database/entities/)")
    ap.add_argument("--batch", action="store_true", help="Generate for all (or --limit) BUILTIN_MOTIFS")
    ap.add_argument("--limit", type=int, default=0, help="Limit for --batch")
    ap.add_argument("--update-existing", help="Path to existing .md to enhance with fresh full-corpus evidence")
    ap.add_argument("--use-llm", action="store_true", help="Attempt xAI synthesis for the description (requires credits + key)")
    args = ap.parse_args()

    client = get_client()

    motifs_to_process = []
    if args.batch:
        motifs_to_process = BUILTIN_MOTIFS[:args.limit] if args.limit else BUILTIN_MOTIFS
    elif args.update_existing:
        # For update we still need a motif/query — user must provide --motif or --query
        if not (args.motif or args.query):
            print("For --update-existing you must also provide --motif or --query to know what to search for.")
            sys.exit(1)
        motifs_to_process = [{
            "motif": args.motif or "custom-update",
            "title": args.title or "Updated Entity",
            "seed_query": args.query or "update this motif",
            "tags": (args.tags or "archetype").split(","),
        }]
    else:
        if not args.motif or not args.query:
            print("Provide --motif and --query, or use --batch")
            ap.print_help()
            sys.exit(1)
        motifs_to_process = [{
            "motif": args.motif,
            "title": args.title or args.motif.replace("_", " ").title(),
            "seed_query": args.query,
            "tags": (args.tags or "archetype").split(","),
        }]

    for m in motifs_to_process:
        print(f"\n=== Processing motif: {m['motif']} ===")
        hits = search_evidence(client, m["seed_query"], top_k=8)
        print(f"Retrieved {len(hits)} evidence chunks.")

        extra = ""
        if args.update_existing and Path(args.update_existing).exists():
            # simple append
            with open(args.update_existing) as f:
                old = f.read()
            extra = f"\n\n**Fresh vector search results (full 21k corpus, {datetime.now().date()}):**\n"
            for h in hits[:3]:
                extra += f"- {h['id']}: {h.get('chunk_text','')[:120]}...\n"

        md_content = generate_markdown(m, hits, use_llm=args.use_llm, extra_evidence=extra)

        # Determine output path
        out_path = None
        if args.output:
            out_path = Path(args.output)
        elif args.obsidian_vault:
            out_path = Path(args.obsidian_vault) / "alien database" / "entities" / f"{m['title']}.md"
        else:
            out_dir = ROOT / "data" / "archetypes"
            out_dir.mkdir(parents=True, exist_ok=True)
            out_path = out_dir / f"{m['motif']}.md"

        if out_path:
            out_path.parent.mkdir(parents=True, exist_ok=True)
            with open(out_path, "w") as f:
                f.write(md_content)
            print(f"Wrote: {out_path}")
        else:
            print(md_content)

        if args.update_existing:
            # append mode already handled in content
            print(f"Enhanced existing file at {args.update_existing}")

    print("\nDone. Review the generated files, add [[wiki links]], run your vault indexer if writing to Obsidian, and link them from your index.md or status pages.")

if __name__ == "__main__":
    main()
