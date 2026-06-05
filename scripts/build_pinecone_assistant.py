#!/usr/bin/env python3
"""
Build a Pinecone Assistant backed by the alien-db UAP/NUFORC data.

This creates (or reuses) a Pinecone Assistant and uploads full sighting reports
as files (with rich metadata for filtering). The Assistant handles its own
chunking + embeddings internally.

Usage examples:
  # Small test set (recommended first)
  python scripts/build_pinecone_assistant.py --limit 200

  # Full corpus (can take a long time + cost; monitor operations)
  python scripts/build_pinecone_assistant.py --limit 0

  # Specific assistant name
  python scripts/build_pinecone_assistant.py --name alien-db-uap --limit 500

After upload, chat in the Pinecone console (Assistant playground) or via the API
(see the chat example at the bottom of this script or in the Pinecone docs).

Note: This uses Pinecone's managed Assistant (different from the custom RAG in ui/app.py
which uses the existing alien-db-uap index + client-side e5 embeddings + exact traces).
Use this for a quick managed chat experience; keep the custom one for glass-box research.
"""

import argparse
import json
import os
import time
from io import BytesIO
from pathlib import Path
from typing import Dict, Any, Optional

from dotenv import load_dotenv
from pinecone import Pinecone
from pinecone.client.assistants.models import Message  # type: ignore

load_dotenv()

DEFAULT_NAME = "alien-db-uap"
DEFAULT_INSTRUCTIONS = (
    "You are an objective researcher analyzing patterns in reported anomalous experiences "
    "from the NUFORC public database. Identify recurring motifs, common sequences of events, "
    "variations in descriptions, potential clusters or archetypes, and any notable similarities "
    "or differences. Note possible cultural, psychological, or mundane explanations where relevant. "
    "Structure your output clearly. Always ground claims in the specific sighting reports provided. "
    "All data is anecdotal and unverified. Explicitly surface limitations and alternative explanations."
)

PROJECT_ROOT = Path(__file__).parent.parent
DEFAULT_DATA = PROJECT_ROOT / "data" / "processed" / "nuforc-full.jsonl"


def get_pc() -> Pinecone:
    key = os.getenv("PINECONE_API_KEY")
    if not key:
        raise RuntimeError("PINECONE_API_KEY not found in environment / .env")
    return Pinecone(api_key=key)


def create_or_get_assistant(
    pc: Pinecone,
    name: str,
    instructions: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> Any:
    try:
        existing = pc.assistants.describe(name=name)
        print(f"Assistant '{name}' already exists (status: {getattr(existing, 'status', 'unknown')}). Reusing it.")
        return existing
    except Exception:
        pass

    print(f"Creating assistant '{name}' ...")
    assistant = pc.assistants.create(
        name=name,
        instructions=instructions,
        metadata=metadata or {"project": "alien-db", "source": "NUFORC", "version": "v0.1"},
        region="us",
        timeout=120,
    )
    print(f"Created assistant: {assistant.name} (status: {getattr(assistant, 'status', 'initializing')})")
    return assistant


def upload_report(
    pc: Pinecone,
    assistant_name: str,
    report: Dict[str, Any],
    file_id: Optional[str] = None,
) -> Any:
    """Upload one full sighting report as a file with metadata."""
    sid = str(report.get("id", "unknown"))
    narrative = report.get("narrative", "") or ""
    if not narrative.strip():
        return None

    # Build a clean document for the assistant (narrative + key structured facts)
    header = (
        f"Sighting ID: {sid}\n"
        f"Occurred: {report.get('occurred', 'unknown')}\n"
        f"Reported: {report.get('reported', 'unknown')}\n"
        f"Location: {report.get('location', 'unknown')}\n"
        f"City/State/Country: {report.get('city', '')}, {report.get('state', '')}, {report.get('country', '')}\n"
        f"Shape: {report.get('shape', 'unknown')}\n"
        f"Duration: {report.get('duration', 'unknown')}\n"
        f"Observer count: {report.get('observer_count', 'unknown')}\n"
        f"Possible abduction: {report.get('possible_abduction', False)}\n"
        f"Missing time: {report.get('missing_time', False)}\n"
        f"Animals reacted: {report.get('animals_reacted', False)}\n"
        f"Marks on body: {report.get('marks_on_body', False)}\n"
        f"Landed: {report.get('landed', False)}\n"
        f"Lights on object: {report.get('lights_on_object', False)}\n\n"
    )
    content = header + narrative

    # Rich metadata for filtering in chat (shape, abduction flag, etc.)
    meta = {
        "id": sid,
        "shape": report.get("shape"),
        "possible_abduction": bool(report.get("possible_abduction")),
        "location": report.get("location"),
        "country": report.get("country"),
        "occurred": str(report.get("occurred")),
        "source": "NUFORC",
    }
    # Clean None values
    meta = {k: v for k, v in meta.items() if v is not None}

    stream = BytesIO(content.encode("utf-8"))
    fname = f"{sid}.txt"

    try:
        resp = pc.assistants.upload_file(
            assistant_name=assistant_name,
            file_stream=stream,
            file_name=fname,
            metadata=meta,
            file_id=file_id or sid,  # stable ID = sighting ID
            timeout=60,
        )
        return resp
    except Exception as e:
        print(f"  Failed to upload {sid}: {e}")
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", default=DEFAULT_NAME, help="Name for the Pinecone Assistant")
    ap.add_argument("--instructions", default=DEFAULT_INSTRUCTIONS, help="System instructions for the assistant")
    ap.add_argument("--data", type=Path, default=DEFAULT_DATA, help="Path to nuforc-*.jsonl (full reports preferred)")
    ap.add_argument("--limit", type=int, default=500, help="Max reports to upload (0 = all; start small!)")
    ap.add_argument("--sleep", type=float, default=0.05, help="Sleep between uploads to be nice to the API")
    args = ap.parse_args()

    if not args.data.exists():
        print(f"Data file not found: {args.data}")
        return

    pc = get_pc()

    assistant = create_or_get_assistant(
        pc,
        name=args.name,
        instructions=args.instructions,
        metadata={"project": "alien-db", "corpus": "NUFORC-full", "embeddings": "custom-e5-in-project"},
    )

    print(f"\nUploading reports from {args.data} (limit={args.limit or 'ALL'}) to assistant '{args.name}'...")
    print("This is asynchronous — files will be processed after upload. Use list_files / describe_file to monitor.")

    count = 0
    with args.data.open() as f:
        for line in f:
            if not line.strip():
                continue
            try:
                rec = json.loads(line)
            except Exception:
                continue

            upload_report(pc, assistant.name, rec)
            count += 1
            if count % 50 == 0:
                print(f"  Uploaded {count} reports so far...")
            if args.limit and count >= args.limit:
                break
            time.sleep(args.sleep)

    print(f"\nDone. Uploaded ~{count} reports.")
    print(f"\nNext steps:")
    print(f"  1. Go to the Pinecone console → Assistants → '{args.name}' to chat in the playground.")
    print(f"  2. Or use the API (example below).")
    print(f"  3. To see files: pc.assistants.list_files(assistant_name='{args.name}')")
    print(f"\nExample chat code (run in Python):")
    print(f"""
from pinecone import Pinecone
from pinecone_plugins.assistant.models.chat import Message  # or just use dicts

pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
msgs = [Message(role="user", content="What recurring patterns appear in abduction-flagged triangle reports?")]
resp = pc.assistants.chat(assistant_name="{args.name}", messages=msgs, filter={{"possible_abduction": True, "shape": "Triangle"}})
print(resp.message.content)
print("Citations:", resp.citations)
""")


if __name__ == "__main__":
    main()
