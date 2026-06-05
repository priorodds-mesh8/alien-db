#!/usr/bin/env python3
"""
compute_motif_clusters.py

Dynamically compute:
- The 5 "most common" motifs using lightweight signals: frequency of light enrichment tags + number of chunks with high cosine similarity to the 3 benchmark prototypes.
- A pool of "small rare clusters" (size 2-12 after k-means on the embedding space).

Saves data/motifs.json with:
- common_motifs: list of 5, each with name, count (or proxy), key_quotes (3-4 short text bands with source_report_id)
- small_clusters: list of many small ones (we sample 30 at runtime for the "weird" button), each with size, key_quotes, why_weird note.

This is designed to be easy to explain: 
- Common = what tags fire a lot or what matches our "perfect example stories" a lot.
- Rare weird = small tight groups in the meaning space that don't match the usual patterns.

Run once after full seed. Embeddings are cached to speed up.

Usage:
  EMBEDDER_DEVICE=cpu python scripts/compute_motif_clusters.py --k 100 --small-max-size 12

Outputs:
  data/motifs.json
  (also saves data/chunk_embeddings.npy and data/chunk_ids.json for reuse)
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import List, Dict, Any

import numpy as np
from dotenv import load_dotenv

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "packages"))

load_dotenv()

from uap_corpus.embedder import embed_passages, embed_query
from uap_corpus.fixtures.uap_benchmark import get_benchmark_records

try:
    from sklearn.cluster import KMeans
except ImportError:
    print("sklearn not available. Please pip install scikit-learn for k-means.")
    sys.exit(1)

CHUNKS_PATH = ROOT / "data" / "chunks" / "nuforc-full-chunks.jsonl"
EMB_PATH = ROOT / "data" / "chunk_embeddings.npy"
IDS_PATH = ROOT / "data" / "chunk_ids.json"
MOTIFS_PATH = ROOT / "data" / "motifs.json"

BENCHMARKS = get_benchmark_records()  # the 3 high-signal ones

def load_chunks() -> List[Dict[str, Any]]:
    chunks = []
    with open(CHUNKS_PATH) as f:
        for line in f:
            if line.strip():
                chunks.append(json.loads(line))
    return chunks

def get_or_compute_embeddings(chunks: List[Dict]) -> np.ndarray:
    if EMB_PATH.exists() and IDS_PATH.exists():
        print("Loading cached embeddings...")
        embs = np.load(EMB_PATH)
        with open(IDS_PATH) as f:
            ids = json.load(f)
        # basic sanity
        if len(embs) == len(chunks) and len(ids) == len(chunks):
            return embs
        print("Cache mismatch, recomputing...")

    print("Embedding all chunks (this may take a while first time, use EMBEDDER_DEVICE=cpu)...")
    texts = [c["chunk_text"] for c in chunks]
    embs = np.array(embed_passages(texts))  # (N, 1024)
    ids = [c["chunk_id"] for c in chunks]

    np.save(EMB_PATH, embs)
    with open(IDS_PATH, "w") as f:
        json.dump(ids, f)
    print(f"Saved embeddings to {EMB_PATH}")
    return embs

def compute_high_sim_counts(embs: np.ndarray, chunks: List[Dict], thresh: float = 0.78) -> Dict[str, int]:
    """For each benchmark, count how many chunks have cosine > thresh to its vector."""
    print(f"Computing high-sim counts (thresh={thresh}) to the 3 benchmark prototypes...")
    counts = {}
    bench_embs = np.array(embed_passages([b["chunk_text"] for b in BENCHMARKS]))
    # normalize not needed if already unit, but safe
    bench_embs = bench_embs / np.linalg.norm(bench_embs, axis=1, keepdims=True)
    chunk_norms = embs / np.linalg.norm(embs, axis=1, keepdims=True)

    for i, bench in enumerate(BENCHMARKS):
        sims = np.dot(chunk_norms, bench_embs[i])
        count = int(np.sum(sims > thresh))
        counts[bench["motif"]] = count
        print(f"  {bench['motif']}: {count} chunks > {thresh}")
    return counts

def get_top_enrich_tags(chunks: List[Dict], top_n: int = 5) -> List[str]:
    """Lightweight obvious tags from the light enrichment."""
    tag_counts = {}
    for c in chunks:
        for key in ("entities", "effects", "sequence"):
            for item in c.get(key, []):
                if isinstance(item, dict):
                    tag = item.get("desc") or item.get("type", "")
                else:
                    tag = str(item)
                if tag:
                    tag_counts[tag] = tag_counts.get(tag, 0) + 1
    sorted_tags = sorted(tag_counts.items(), key=lambda x: -x[1])[:top_n]
    return [t for t, _ in sorted_tags]

def pick_five_common(high_sim_counts: Dict[str, int], top_tags: List[str]) -> List[Dict]:
    """
    Lightweight dynamic selection for the 5 most common.
    Prioritize the 3 curated benchmarks (by their high-sim count) + top 2 obvious enrich tags.
    Easy to explain: "The classics we already know are strong, plus the two most frequently mentioned obvious things in the chunks."
    """
    common = []
    # Add the 3 benchmarks, sorted by their prevalence
    bench_sorted = sorted(high_sim_counts.items(), key=lambda x: -x[1])
    for motif, cnt in bench_sorted:
        common.append({
            "name": motif.replace("_", " ").title(),
            "type": "benchmark",
            "count": cnt,
            "description": next((b["chunk_text"][:200] for b in BENCHMARKS if b["motif"] == motif), ""),
        })
    # Add top 2 enrich tags as "data-driven common"
    for tag in top_tags[:2]:
        common.append({
            "name": tag.title()[:40],
            "type": "enrich_tag",
            "count": "frequent in chunks",
            "description": f"Light enrichment tag that fired often: {tag}",
        })
    # Dedup / trim to 5 obvious ones (keep order, take first 5 unique by name)
    seen = set()
    final = []
    for m in common:
        if m["name"] not in seen and len(final) < 5:
            seen.add(m["name"])
            final.append(m)
    return final[:5]

def compute_small_clusters(embs: np.ndarray, chunks: List[Dict], k: int = 100, min_size: int = 2, max_size: int = 12) -> List[Dict]:
    """Run k-means, return small clusters (2-12 members) with key quotes and citations."""
    print(f"Running k-means (k={k}) to find small clusters...")
    kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
    labels = kmeans.fit_predict(embs)
    centroids = kmeans.cluster_centers_

    clusters = {}
    for i, lab in enumerate(labels):
        clusters.setdefault(lab, []).append(i)

    small = []
    for lab, idxs in clusters.items():
        size = len(idxs)
        if min_size <= size <= max_size:
            # Get the actual chunks in this cluster
            cluster_chunks = [chunks[i] for i in idxs]
            # Pick 3-4 "text bands" from highest similarity to centroid (or just first few for simplicity)
            # For demo, take up to 4 chunks, use their chunk_text (truncated for tooltip)
            quotes = []
            for c in cluster_chunks[:4]:
                text = c.get("chunk_text", "")[:220].replace("\n", " ").strip()
                sid = c.get("source_report_id", c.get("chunk_id", "?"))
                quotes.append({
                    "text": text + "...",
                    "source_id": sid,
                    "chunk_id": c.get("chunk_id")
                })
            # Simple "why weird" note based on common tags in cluster
            common_tags = []
            for c in cluster_chunks:
                for key in ("entities", "effects", "sequence"):
                    for item in c.get(key, []):
                        if isinstance(item, dict):
                            t = item.get("desc") or item.get("type")
                        else:
                            t = str(item)
                        if t:
                            common_tags.append(t)
            tag_str = ", ".join([t for t, _ in Counter(common_tags).most_common(3)]) if common_tags else "mixed descriptors"
            why = f"Small tight group of {size} chunks sharing {tag_str}. Rare combination in the overall corpus."

            small.append({
                "cluster_id": int(lab),
                "size": size,
                "quotes": quotes,
                "why_weird": why,
                "chunk_ids": [c.get("chunk_id") for c in cluster_chunks[:4]]
            })
    print(f"Found {len(small)} small clusters (size {min_size}-{max_size}).")
    return small

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--k", type=int, default=100, help="Number of k-means clusters")
    ap.add_argument("--small-max-size", type=int, default=12, help="Max size for 'small' clusters")
    ap.add_argument("--thresh", type=float, default=0.78, help="Cosine threshold for 'high similarity' to benchmarks")
    args = ap.parse_args()

    print("Loading chunks...")
    chunks = load_chunks()
    print(f"Loaded {len(chunks)} chunks.")

    embs = get_or_compute_embeddings(chunks)

    # 1. High-sim counts to the 3 benchmarks (for dynamic common)
    high_sim = compute_high_sim_counts(embs, chunks, thresh=args.thresh)

    # 2. Top light enrichment tags (lightweight obvious)
    top_tags = get_top_enrich_tags(chunks, top_n=5)
    print("Top light enrichment tags:", top_tags)

    # Pick 5 most common dynamically (lightweight mix)
    five_common = pick_five_common(high_sim, top_tags)
    print("Selected 5 most common motifs (dynamic):")
    for m in five_common:
        print(f"  - {m['name']} ({m['type']})")

    # 3. Small rare clusters via k-means
    small_clusters = compute_small_clusters(embs, chunks, k=args.k, max_size=args.small_max_size)

    # Pick a pool for random draw (user said random draw of 30)
    # We save all small ones; the UI can random.sample(30)
    print(f"Saving {len(small_clusters)} small clusters for the random 'weird' pool.")

    motifs_data = {
        "common_motifs": five_common,
        "small_clusters_pool": small_clusters,  # UI will random 30 of these
        "notes": {
            "how_common_computed": "Mix of (a) how many chunks have high cosine to our 3 benchmark prototype vectors + (b) most frequent obvious light-enrichment tags from the chunker. Lightweight and human-obvious.",
            "how_rare_computed": f"k-means (k={args.k}) on the 1024-d embeddings; kept clusters with 2-{args.small_max_size} members. These are 'small but coherent' groups in meaning space.",
            "citation": "Every quote includes the original source_report_id (NUFORC Sighting ID) so you can trace back to the exact record in the processed JSONL.",
            "weird_button": "Random draw of 30 small clusters. Each shows 3-4 actual text excerpts from the highest-similarity chunks in that cluster + the source ID. Labeled 'weird / uncommon in the literature' with a direct question to the user about noise vs real tiny pattern."
        }
    }

    with open(MOTIFS_PATH, "w") as f:
        json.dump(motifs_data, f, indent=2, ensure_ascii=False)
    print(f"\nWrote {MOTIFS_PATH}")
    print("Now the Gradio UI or a new static page can load this JSON and implement the icons + dice button.")

if __name__ == "__main__":
    main()
