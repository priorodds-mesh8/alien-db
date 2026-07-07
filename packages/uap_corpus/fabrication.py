"""
Fabrication-only evaluation + hybrid-filter helpers for the glass-box UAP RAG.

The whole promise of this project is *trustworthy, provenance-preserving* analysis, so the
fabrication signal must be able to actually fail. The previous `toy_fabrication_eval` floored
the score at 0.6 and only substring-matched five hardcoded strings — it could never report
distrust. This module replaces it with an honest, deterministic, offline claim-level check:

  fabrication = a claim that asserts a STRONG SPECIFIC (a number/time, a proper noun, or a
  quoted term) that does NOT appear anywhere in the retrieved evidence.

Generic hedging ("these are anecdotal, unverified reports") is not fabrication and is not
penalised. There is no floor: a synthesis full of invented specifics scores near 0.

When an LLM key is present the caller may upgrade this to NLI / constrained LLM-judge; the
lexical version is the always-available floor-free baseline and is what the unit tests pin.
"""
import re
from typing import List, Dict, Any

_TOKEN_RE = re.compile(r"[a-z0-9']+")
_NUM_RE = re.compile(r"\d[\d:.,]*")
_PROPER_RE = re.compile(r"\b[A-Z][a-zA-Z]{2,}\b")
_QUOTED_RE = re.compile(r"[\"'“‘]([^\"'”’]{2,})[\"'”’]")

# Words that start sentences / are common enough that a leading capital doesn't make them a
# distinctive proper noun. Kept small and lowercase for membership tests.
_COMMON_CAPS = {
    "the", "a", "an", "these", "this", "that", "those", "their", "there", "they", "some",
    "many", "most", "no", "not", "key", "shapes", "locations", "recurring", "pattern",
    "critical", "local", "note", "notes", "in", "of", "and", "or", "but", "for", "with",
    "reports", "report", "sightings", "sighting", "evidence", "analysis", "query", "results",
    "observers", "observer", "descriptions", "descriptions", "sleep", "hopkins", "jacobs",
    "strieber",  # named in the STATIC disclaimer, not a claim about the evidence
}


def _content_tokens(text: str) -> List[str]:
    return [t for t in _TOKEN_RE.findall(text.lower()) if len(t) > 3]


def _split_claims(synthesis: str) -> List[str]:
    """Split into claim-ish sentences. Skip markdown headers, bare labels, and any block
    explicitly marked STATIC (methodological disclaimer not derived from the chunks)."""
    claims: List[str] = []
    for raw_line in synthesis.split("\n"):
        line = raw_line.strip()
        if not line:
            continue
        # A block the synthesizer flags as a static, non-derived disclaimer is not a claim
        # about the retrieved evidence, so it must not be scored as (un)grounded.
        if "[STATIC]" in line:
            continue
        # Strip markdown decoration
        line = line.lstrip("#>-* ").strip()
        # Drop pure bold labels like "**Shapes in results:**"
        line = re.sub(r"^\*\*[^*]+\*\*:?\s*", "", line).strip("* ").strip()
        if not line:
            continue
        for sentence in re.split(r"(?<=[.!?])\s+", line):
            s = sentence.strip()
            if len(s.split()) >= 4:
                claims.append(s)
    return claims


def _strong_specifics(claim: str) -> List[str]:
    specifics = []
    specifics += _NUM_RE.findall(claim)
    specifics += _QUOTED_RE.findall(claim)
    for m in _PROPER_RE.findall(claim):
        if m.lower() not in _COMMON_CAPS:
            specifics.append(m)
    # de-dupe, keep order
    seen = set()
    out = []
    for s in specifics:
        k = s.lower().strip()
        if k and k not in seen:
            seen.add(k)
            out.append(s)
    return out


def fabrication_eval(synthesis: str, evidence_chunks: List[str]) -> Dict[str, Any]:
    """Claim-level fabrication check against the retrieved evidence ONLY. No score floor.

    Returns: score in [0,1], `fabricated` (list of offending claim strings), `flagged`
    (per-claim detail with the unsupported specifics + best supporting evidence index), and
    `claims` (every evaluated claim with its grounding + citation). Higher score = better grounded.
    """
    evidence_joined = " ".join(evidence_chunks or [])
    evidence_low = evidence_joined.lower()
    evidence_tokens = set(_TOKEN_RE.findall(evidence_low))
    per_chunk_tokens = [set(_TOKEN_RE.findall((c or "").lower())) for c in (evidence_chunks or [])]

    claims = _split_claims(synthesis)
    if not claims:
        return {"score": 1.0, "fabricated": [], "flagged": [], "claims": [],
                "notes": "No substantive claims to evaluate."}

    flagged: List[Dict[str, Any]] = []
    detail: List[Dict[str, Any]] = []
    grounded = 0

    for c in claims:
        specifics = _strong_specifics(c)
        unsupported = [s for s in specifics if s.lower() not in evidence_low]

        toks = _content_tokens(c)
        overlap = sum(1 for t in toks if t in evidence_tokens)
        ratio = round(overlap / len(toks), 3) if toks else 1.0

        # Best supporting evidence chunk (for a provenance citation on grounded claims)
        best_idx, best_hits = -1, 0
        for i, ct in enumerate(per_chunk_tokens):
            h = sum(1 for t in toks if t in ct)
            if h > best_hits:
                best_hits, best_idx = h, i

        is_fabricated = bool(unsupported)
        if is_fabricated:
            flagged.append({"claim": c[:200], "unsupported_specifics": unsupported[:6], "grounding": ratio})
        else:
            grounded += 1
        detail.append({
            "claim": c[:200],
            "grounding": ratio,
            "fabricated": is_fabricated,
            "cite_evidence_index": best_idx if best_idx >= 0 else None,
        })

    score = round(grounded / len(claims), 3)
    return {
        "score": score,
        "fabricated": [f["claim"] for f in flagged],
        "flagged": flagged,
        "claims": detail,
        "notes": ("Claim-level lexical grounding vs retrieved evidence only; no score floor. "
                  "A claim is fabricated iff it asserts a specific (number, proper noun, quoted "
                  "term) absent from the evidence. Add XAI/ANTHROPIC key to upgrade to LLM-judge/NLI."),
    }


# NUFORC canonical shape labels are Title-case ("Triangle", "Light", ...). The Gradio dropdown
# historically emitted lowercase, so `{"$eq": "triangle"}` matched nothing (Pinecone $eq is
# case-sensitive). Build a case-robust $in filter so retrieval works regardless of stored casing
# and without needing a re-seed. (Durable fix on next seed: index a normalized `shape_lc` field.)
def build_shape_filter(shape: str) -> Dict[str, Any]:
    """Return a Pinecone metadata filter fragment for a shape value, robust to casing.
    Empty/whitespace input returns an empty dict (no filter)."""
    if not shape or not shape.strip():
        return {}
    s = shape.strip()
    variants = {s, s.lower(), s.upper(), s.capitalize(), s.title()}
    return {"shape": {"$in": sorted(variants)}}
