#!/usr/bin/env python3
"""
Seed UAP chunks into Pinecone with REAL client embeddings (e5-large-v2 1024d normalized).

- Uses packages/uap_corpus/embedder.py (passage: prefix) + explicit /vectors/upsert
- Hybrid: semantic cosine + metadata filters (shape, possible_abduction, etc.)
- Run with --reset to delete prior ns contents first (recommended when switching from pseudo/integrated vecs)

Usage:
  python scripts/seed_uap.py --ns nuforc-v0.1-proto --input data/chunks/nuforc-chunks.jsonl --reset
"""
import argparse
import json
import sys
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()  # Load local .env if present

root = Path(__file__).parent.parent
sys.path.insert(0, str(root / "packages"))
from uap_corpus.pinecone_client import PineconeClient  # type: ignore


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", dest="input_path", type=Path, default=Path("data/chunks/nuforc-chunks.jsonl"))
    ap.add_argument("--ns", default="nuforc-v0.1-proto")
    ap.add_argument("--reset", action="store_true", help="Delete all in namespace before upsert (clean for new full ingest)")
    ap.add_argument("--resume", action="store_true", help="Skip chunk_ids already present in the namespace (resume a killed seed without re-embedding)")
    ap.add_argument("--batch-size", type=int, default=64, help="Chunks per embed+upsert batch (higher = faster, more mem)")
    args = ap.parse_args()

    if args.reset and args.resume:
        print("Refusing --reset and --resume together (--reset wipes the namespace, defeating resume).")
        sys.exit(2)

    client = PineconeClient.from_env()
    if not client:
        print("No PINECONE_API_KEY — would upsert locally or to a different store.")
        with args.input_path.open() as f:
            count = sum(1 for _ in f)
        print(f"Would have sent {count} chunk records with embeddings.")
        return

    client.namespace = args.ns

    if args.reset:
        print(f"Deleting ALL vectors in ns={args.ns} ... (clean full run)")
        client.delete_namespace(args.ns)
        print("Delete complete.")

    def _flush(batch, total, skipped):
        """Embed+upsert a batch, skipping ids already present when --resume is set."""
        if args.resume and batch:
            existing = client.fetch_existing_ids([c.get("chunk_id") for c in batch if c.get("chunk_id")])
            before = len(batch)
            batch = [c for c in batch if c.get("chunk_id") not in existing]
            skipped += before - len(batch)
        n = client.upsert_chunks(batch) if batch else 0
        return total + n, skipped

    print(f"Streaming + embedding + upserting from {args.input_path} to ns={args.ns} "
          f"(batch={args.batch_size}, resume={args.resume}) ...")

    total = 0
    skipped = 0
    batch = []
    with args.input_path.open() as f:
        for line in f:
            if not line.strip():
                continue
            try:
                c = json.loads(line)
            except Exception:
                continue
            batch.append(c)
            if len(batch) >= args.batch_size:
                total, skipped = _flush(batch, total, skipped)
                batch = []
                if total % 1000 == 0 or total <= 512:
                    print(f"  upserted {total} chunks so far (skipped {skipped} already-present)...")

    if batch:
        total, skipped = _flush(batch, total, skipped)

    if args.resume:
        print(f"Resume: skipped {skipped} chunks already present in ns={args.ns}.")

    print(f"\nDone. Total upserted {total} chunks with real embeddings to Pinecone ns={args.ns}")
    print(f"Index: {client.index_name} (dim=1024 cosine, e5-large-v2 client embeddings)")

    # quick stats
    try:
        import urllib.request
        host = client._get_host()
        url = f"{host}/describe_index_stats"
        req = urllib.request.Request(url, headers={"Api-Key": client.api_key, "X-Pinecone-API-Version": "2025-10"})
        with urllib.request.urlopen(req) as r:
            stats = json.loads(r.read())
        ns_stats = stats.get("namespaces", {}).get(args.ns, {})
        print(f"Pinecone ns stats: {ns_stats}")
    except Exception as e:
        print(f"(Could not fetch live stats: {e})")


if __name__ == "__main__":
    main()
