#!/usr/bin/env python3
"""Download (subset or full) kcimc/NUFORC from Hugging Face and emit a clean JSONL.

The HF dataset contains duplicates (~148k unique Sighting IDs out of 591k rows).
We deduplicate by Sighting ID for the "entirety".

Usage:
  # small sample (keeps old behavior)
  python scripts/download_nuforc.py --limit 2000 --out data/processed/nuforc-sample.jsonl

  # the full deduplicated corpus (~147,891 unique reports)
  python scripts/download_nuforc.py --full --out data/processed/nuforc-full.jsonl

Saves records with canonical keys for downstream chunk/enrich. Public dataset (personal/experimental use noted per NUFORC ToS).
"""
import argparse
import json
import sys
from pathlib import Path
from datasets import load_dataset

sys.path.insert(0, str(Path(__file__).parent.parent / "packages"))
from uap_corpus.schema import report_is_valid  # stage-boundary contract

DEFAULT_SAMPLE_OUT = Path("data/processed/nuforc-sample.jsonl")
DEFAULT_FULL_OUT = Path("data/processed/nuforc-full.jsonl")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=2000, help="Max unique records (0 or --full for everything ~148k unique)")
    ap.add_argument("--full", action="store_true", help="Download full deduplicated corpus (ignores --limit or sets to unlimited)")
    ap.add_argument("--out", type=Path, default=None, help="Output jsonl (auto chooses sample vs full if not given)")
    args = ap.parse_args()

    if args.full:
        limit = 0
        out_path = args.out or DEFAULT_FULL_OUT
    else:
        limit = args.limit
        out_path = args.out or DEFAULT_SAMPLE_OUT

    out_path.parent.mkdir(parents=True, exist_ok=True)

    effective_limit = limit if limit > 0 else None
    print(f"Loading kcimc/NUFORC with streaming (dedup by Sighting ID, limit={effective_limit or 'ALL'}) ...")
    ds = load_dataset("kcimc/NUFORC", split="train", streaming=True)

    seen_ids = set()
    written = 0
    total_seen = 0
    invalid = 0

    with out_path.open("w") as f:
        for i, row in enumerate(ds):
            sid = str(row.get("Sighting") or f"nuforc-{i}")
            total_seen += 1
            if sid in seen_ids:
                continue
            seen_ids.add(sid)

            if effective_limit and written >= effective_limit:
                break

            rec = {
                "id": sid,
                "source": "NUFORC",
                "occurred": row.get("Occurred"),
                "reported": row.get("Reported"),
                "location": row.get("Location"),
                "city": None,
                "state": None,
                "country": None,
                "shape": row.get("Shape"),
                "duration": row.get("Duration"),
                "narrative": row.get("Text") or row.get("Summary") or "",
                "observer_count": row.get("No of observers") or 1,
                "possible_abduction": bool(row.get("Possible abduction") or False),
                "missing_time": bool(row.get("Missing Time") or False),
                "marks_on_body": bool(row.get("Marks found on body afterwards") or False),
                "landed": bool(row.get("Landed") or False),
                "lights_on_object": bool(row.get("Lights on object") or False),
                "animals_reacted": bool(row.get("Animals reacted") or False),
                "url": "https://nuforc.org/",
                "raw": row,  # keep original for debugging / future enrichment
            }
            # Stage-boundary check: surface schema drift (renamed/missing fields) without
            # aborting the run — a malformed record is counted, not silently trusted downstream.
            ok, err = report_is_valid(rec)
            if not ok:
                invalid += 1
                if invalid <= 3:
                    print(f"  [schema] report {sid} failed validation: {err.splitlines()[0]}")

            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            written += 1

            if written % 5000 == 0:
                print(f"  written {written} unique (scanned {total_seen})...")

    print(f"Done. Wrote {written} unique records -> {out_path}")
    print(f"(Scanned {total_seen} rows from HF, deduped on Sighting ID. Unique in corpus ~147891)")
    if invalid:
        print(f"[schema] {invalid} record(s) failed the Report contract — inspect before seeding.")

if __name__ == "__main__":
    main()
