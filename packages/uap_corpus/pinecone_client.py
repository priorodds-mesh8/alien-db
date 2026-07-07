"""
Pinecone client for explicit client-side embeddings (real semantic vectors).

Ported/adapted from agentic-sdr-demo/packages/mcp-memory/src/pinecone.ts patterns
but using our local e5-large-v2 (1024d, normalized, passage:/query: prefixes) + direct
/vectors/* REST calls against the dense cosine index (no server-side integrated embedding).

This enables true semantic search (cosine on real embeddings) + metadata hybrid filters.
Current index: dense 1024 cosine (see embedder.py for why e5-large-v2).

chunk_text is stored in metadata for retrieval (no separate storage needed).
All operations are glass-box via events in calling code.
"""
import os
import json
import time
import random
from typing import List, Dict, Any, Optional
import urllib.request
import urllib.error

# Network timeouts (seconds) so a single stalled connection can't hang a
# multi-hour seed or a UI query forever. Data-plane writes get a longer budget.
_HTTP_TIMEOUT = 30
_UPSERT_TIMEOUT = 120

# Retry policy: a transient 429/5xx or a dropped connection should not abort a 1–3 hr seed.
_MAX_ATTEMPTS = 5
_RETRYABLE_STATUS = frozenset({408, 425, 429, 500, 502, 503, 504})


def _is_retryable_status(code: int) -> bool:
    return code in _RETRYABLE_STATUS


def _backoff_seconds(attempt: int, base: float = 0.5, cap: float = 30.0) -> float:
    """Exponential backoff with full jitter. attempt is 0-indexed."""
    expo = min(cap, base * (2 ** attempt))
    return random.uniform(0, expo)


def _urlopen_retry(req: "urllib.request.Request", timeout: float):
    """urlopen with retry/backoff on transient HTTP status and connection errors. Returns the open
    response (caller uses it as a context manager). Raises the last error after _MAX_ATTEMPTS."""
    last_err = None
    for attempt in range(_MAX_ATTEMPTS):
        try:
            return urllib.request.urlopen(req, timeout=timeout)
        except urllib.error.HTTPError as e:
            last_err = e
            if _is_retryable_status(e.code) and attempt < _MAX_ATTEMPTS - 1:
                time.sleep(_backoff_seconds(attempt))
                continue
            raise
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            last_err = e
            if attempt < _MAX_ATTEMPTS - 1:
                time.sleep(_backoff_seconds(attempt))
                continue
            raise
    if last_err:
        raise last_err


def _get_embed_fns():
    """Lazy import so sentence-transformers/torch not required unless actually using Pinecone real path."""
    from .embedder import embed_passages, embed_query
    return embed_passages, embed_query


class PineconeClient:
    def __init__(self, api_key: str, index_name: str = "alien-db-uap", namespace: str = "nuforc-full"):
        self.api_key = api_key
        self.index_name = index_name
        self.namespace = namespace
        self._host: Optional[str] = None

    @classmethod
    def from_env(cls) -> Optional["PineconeClient"]:
        key = os.getenv("PINECONE_API_KEY")
        if not key:
            return None
        idx = os.getenv("PINECONE_INDEX", "alien-db-uap")
        # Default to the full corpus (21,179 chunks) that the UI advertises, not the
        # 105-chunk proto. Override with PINECONE_NAMESPACE=nuforc-v0.1-proto for sample runs.
        ns = os.getenv("PINECONE_NAMESPACE", "nuforc-full")
        return cls(key, idx, ns)

    def _get_host(self) -> str:
        if self._host:
            return self._host
        url = f"https://api.pinecone.io/indexes/{self.index_name}"
        req = urllib.request.Request(url, headers={
            "Api-Key": self.api_key,
            "X-Pinecone-API-Version": "2026-04",
        })
        with _urlopen_retry(req, timeout=_HTTP_TIMEOUT) as resp:
            data = json.loads(resp.read())
        host = data.get("host")
        if not host:
            raise RuntimeError(f"No host for index {self.index_name}")
        self._host = host if host.startswith("http") else f"https://{host}"
        return self._host

    def _build_metadata(self, c: Dict[str, Any]) -> Dict[str, Any]:
        """Flatten chunk + its metadata + enrich fields into Pinecone-safe metadata (str/num/bool/list[str] only; no nulls)."""
        md = dict(c.get("metadata") or {})
        # Ensure core fields; drop None (Pinecone disallows null)
        for k, v in list(md.items()):
            if v is None:
                del md[k]
        md.setdefault("source", c.get("source", "NUFORC") or "NUFORC")
        srid = c.get("source_report_id")
        if srid is not None:
            md.setdefault("source_report_id", srid)
        # chunk_text always in meta for return
        text = c.get("chunk_text") or c.get("text") or ""
        md["chunk_text"] = text
        # Optional enrich (lists of str or simple; complex dicts -> str for safety)
        for k in ("entities", "effects", "sequence"):
            v = c.get(k)
            if v is not None:
                if isinstance(v, list):
                    simple = []
                    for item in v:
                        if isinstance(item, str):
                            simple.append(item)
                        elif isinstance(item, dict):
                            simple.append(item.get("desc") or item.get("type") or str(item)[:100])
                        else:
                            simple.append(str(item)[:100])
                    if simple:
                        md[k] = simple[:10]
                else:
                    md[k] = str(v)[:500]
        # final pass: remove any remaining None
        for k, v in list(md.items()):
            if v is None:
                del md[k]
        return md

    def upsert_chunks(self, chunks: List[Dict[str, Any]], batch_size: int = 80) -> int:
        """
        Real embeddings path: embed chunk_text with e5 (passage:), upsert explicit vectors + metadata (incl chunk_text).
        Replaces prior integrated/records attempts (which don't match our plain dense index + search needs).
        """
        if not chunks:
            return 0
        embed_passages, _ = _get_embed_fns()
        texts = [(c.get("chunk_text") or c.get("text") or "") for c in chunks]
        vectors = embed_passages(texts)
        # Build records for vector upsert: each has id + metadata (with chunk_text inside)
        records = []
        for c in chunks:
            rec = {
                "chunk_id": c.get("chunk_id") or c.get("_id"),
                "chunk_text": c.get("chunk_text") or c.get("text") or "",
                "metadata": self._build_metadata(c),
            }
            records.append(rec)
        return self.upsert_vectors(records, vectors, batch_size=batch_size)

    def upsert_vectors(self, records: List[Dict[str, Any]], vectors: List[List[float]], batch_size: int = 100) -> int:
        """Explicit vector upsert to /vectors/upsert. records[i] provides id + metadata (chunk_text inside metadata)."""
        if len(records) != len(vectors):
            raise ValueError("records and vectors length must match")
        host = self._get_host()
        count = 0
        for i in range(0, len(records), batch_size):
            batch_recs = records[i:i + batch_size]
            batch_vecs = vectors[i:i + batch_size]
            vecs = []
            for rec, vec in zip(batch_recs, batch_vecs):
                mid = rec.get("chunk_id") or rec.get("_id") or rec.get("id")
                meta = dict(rec.get("metadata", {}))
                # ensure chunk_text
                if "chunk_text" not in meta and rec.get("chunk_text"):
                    meta["chunk_text"] = rec["chunk_text"]
                v = {
                    "id": mid,
                    "values": vec,
                    "metadata": meta,
                }
                vecs.append(v)
            body = {"vectors": vecs, "namespace": self.namespace}
            req = urllib.request.Request(
                f"{host}/vectors/upsert",
                data=json.dumps(body).encode(),
                headers={
                    "Api-Key": self.api_key,
                    "Content-Type": "application/json",
                    "X-Pinecone-API-Version": "2025-10",
                },
                method="POST"
            )
            try:
                with _urlopen_retry(req, timeout=_UPSERT_TIMEOUT) as r:
                    r.read()
                count += len(batch_recs)
            except urllib.error.HTTPError as e:
                raise RuntimeError(f"Pinecone vectors upsert failed: {e.read()[:400]}") from e
        return count

    def delete_namespace(self, namespace: Optional[str] = None) -> None:
        """Delete all vectors in the namespace (for clean re-seed with new embeddings)."""
        ns = namespace or self.namespace
        host = self._get_host()
        body = {"deleteAll": True, "namespace": ns}
        req = urllib.request.Request(
            f"{host}/vectors/delete",
            data=json.dumps(body).encode(),
            headers={
                "Api-Key": self.api_key,
                "Content-Type": "application/json",
                "X-Pinecone-API-Version": "2025-10",
            },
            method="POST"
        )
        try:
            with _urlopen_retry(req, timeout=_UPSERT_TIMEOUT) as r:
                r.read()
        except urllib.error.HTTPError as e:
            # 404 or empty ok-ish
            if e.code not in (404,):
                raise RuntimeError(f"Pinecone delete failed: {e.read()[:300]}") from e

    def fetch_existing_ids(self, ids: List[str], batch_size: int = 100) -> set:
        """Return the subset of `ids` already present in the namespace (via /vectors/fetch).
        Lets a killed seed resume by skipping vectors that were already upserted (ids are
        deterministic: '<report_id>-c<chunk_index>')."""
        existing = set()
        if not ids:
            return existing
        host = self._get_host()
        import urllib.parse
        for i in range(0, len(ids), batch_size):
            chunk = ids[i:i + batch_size]
            qs = urllib.parse.urlencode([("ids", x) for x in chunk] + [("namespace", self.namespace)])
            req = urllib.request.Request(
                f"{host}/vectors/fetch?{qs}",
                headers={"Api-Key": self.api_key, "X-Pinecone-API-Version": "2025-10"},
            )
            try:
                with _urlopen_retry(req, timeout=_HTTP_TIMEOUT) as r:
                    data = json.loads(r.read())
                existing.update((data.get("vectors") or {}).keys())
            except urllib.error.HTTPError as e:
                # A fetch failure shouldn't abort a resume; treat as "unknown -> not existing".
                if e.code not in (404,):
                    raise
        return existing

    def search(self, query: str, top_k: int = 8, filters: Optional[Dict] = None) -> List[Dict]:
        """
        Real semantic search: embed query with e5 (query: prefix), vector search + optional metadata filter (hybrid).
        Returns hits with id, score (cosine), chunk_text, metadata (other fields).
        """
        if not query or not query.strip():
            return []
        embed_passages, embed_query = _get_embed_fns()
        qvec = embed_query(query)
        host = self._get_host()
        body: Dict[str, Any] = {
            "namespace": self.namespace,
            "vector": qvec,
            "topK": top_k,
            "includeMetadata": True,
        }
        if filters:
            body["filter"] = filters
        req = urllib.request.Request(
            f"{host}/query",
            data=json.dumps(body).encode(),
            headers={
                "Api-Key": self.api_key,
                "Content-Type": "application/json",
                "X-Pinecone-API-Version": "2025-10",
            },
            method="POST"
        )
        with _urlopen_retry(req, timeout=_HTTP_TIMEOUT) as resp:
            data = json.loads(resp.read())
        matches = data.get("matches", []) or data.get("result", {}).get("hits", [])
        out = []
        for m in matches:
            meta = m.get("metadata") or {}
            out.append({
                "id": m.get("id") or m.get("_id"),
                "score": m.get("score"),
                "chunk_text": meta.get("chunk_text", ""),
                "metadata": {k: v for k, v in meta.items() if k != "chunk_text"},
            })
        return out

    def local_fallback_search(self, records: List[Dict], query: str, top_k: int = 8, filters: Optional[Dict] = None) -> List[Dict]:
        """Pure python token overlap fallback (same spirit as mcp-memory localSearch)."""
        q = set(query.lower().split())
        scored = []
        for r in records:
            md = r.get("metadata", {})
            if filters:
                if "possible_abduction" in filters and md.get("possible_abduction") != filters.get("possible_abduction"):
                    continue
                if "shape" in filters and md.get("shape") != filters.get("shape"):
                    continue
            text = (r.get("chunk_text") or "") + " " + str(md)
            score = sum(len(w) for w in q if w in text.lower())
            if score:
                scored.append((score, r))
        scored.sort(reverse=True)
        return [{"id": r.get("chunk_id"), "score": s, "chunk_text": r.get("chunk_text"), "metadata": r.get("metadata")} for s, r in scored[:top_k]]

    # Back-compat alias used in some older scripts
    def query(self, query: str, top_k: int = 8, filters: Optional[Dict] = None) -> List[Dict]:
        return self.search(query, top_k=top_k, filters=filters)
