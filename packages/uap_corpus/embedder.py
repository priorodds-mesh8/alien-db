"""
Embedding utilities for the UAP corpus.

We use a strong local model (intfloat/e5-large-v2, 1024 dim) for now because:
- Matches our Pinecone index dimension.
- Excellent retrieval performance on benchmarks (especially with proper prefixes).
- No extra API key/cost for embeddings (unlike Voyage or OpenAI).

For queries vs documents, e5 models perform best with "query: " and "passage: " prefixes.

This module is designed to be swappable later (e.g. Voyage, OpenAI text-embedding-3-large + dim change, or Pinecone integrated).

Usage:
    from packages.uap_corpus.embedder import embed_passages, embed_query

    # For storing chunks
    vectors = embed_passages([chunk["chunk_text"] for chunk in chunks])

    # For searching
    qvec = embed_query(user_query)
"""

from typing import List
import os
import numpy as np

_model = None
MODEL_NAME = "intfloat/e5-large-v2"  # 1024 dim, strong retriever


def get_model():
    global _model
    if _model is None:
        # Lazy import so we don't require torch/sentence-transformers unless actually embedding
        import torch
        from sentence_transformers import SentenceTransformer

        # Allow override for large batch jobs (MPS can have slow first-compile or poor throughput
        # for some models on certain torch/MPS setups; cpu often faster/more reliable for bulk).
        device = os.getenv("EMBEDDER_DEVICE")
        if not device:
            if torch.backends.mps.is_available():
                device = "mps"
            elif torch.cuda.is_available():
                device = "cuda"
            else:
                device = "cpu"
        print(f"[embedder] Loading {MODEL_NAME} on device={device} (for full dataset runs this can take time on first encode; set EMBEDDER_DEVICE=cpu to force)")
        _model = SentenceTransformer(MODEL_NAME, device=device)
        # e5 models work well with normalization for cosine
        _model.max_seq_length = 512  # safe default
    return _model


def embed_passages(texts: List[str]) -> List[List[float]]:
    """Embed document/chunk texts (use 'passage:' prefix)."""
    if not texts:
        return []
    model = get_model()
    prefixed = [f"passage: {t}" for t in texts]
    embeddings = model.encode(
        prefixed,
        normalize_embeddings=True,
        show_progress_bar=len(texts) > 1000,
        convert_to_numpy=True,
        batch_size=64,  # good throughput for full dataset runs
    )
    return embeddings.tolist()


def embed_query(text: str) -> List[float]:
    """Embed a search query (use 'query:' prefix)."""
    if not text or not text.strip():
        # Return a zero vector as fallback (bad idea in prod, but for demo)
        return [0.0] * 1024
    model = get_model()
    prefixed = f"query: {text}"
    embedding = model.encode(
        [prefixed],
        normalize_embeddings=True,
        show_progress_bar=False,
        convert_to_numpy=True,
        batch_size=8,
    )[0]
    return embedding.tolist()


def get_embedding_dimension() -> int:
    return 1024
