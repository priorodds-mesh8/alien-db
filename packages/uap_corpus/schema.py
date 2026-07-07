"""
Shared Pydantic schema for the corpus pipeline, validated at each stage boundary.

The pipeline is: download_nuforc.py -> Report records -> chunk_and_enrich.py -> Chunk records ->
seed_uap.py -> Pinecone. Each hand-off previously passed loose dicts, so a field renamed or dropped
in one stage failed silently downstream (e.g. the boolean flags that never reached Pinecone). These
models are the contract: `validate_report` / `validate_chunk` normalize types and surface drift.

Both models allow extra keys (e.g. download keeps `raw`, `city/state/country`) so validation is a
guardrail, not a straitjacket.
"""
from typing import Optional, List, Any
from pydantic import BaseModel, ValidationError, field_validator

# The six boolean report flags that must survive all the way to chunk metadata.
BOOLEAN_FLAGS = (
    "possible_abduction",
    "missing_time",
    "marks_on_body",
    "landed",
    "lights_on_object",
    "animals_reacted",
)


class Report(BaseModel):
    """One deduplicated NUFORC sighting, as emitted by download_nuforc.py."""
    model_config = {"extra": "allow"}

    id: str
    source: str = "NUFORC"
    occurred: Optional[str] = None
    reported: Optional[str] = None
    location: Optional[str] = None
    shape: Optional[str] = None
    duration: Optional[str] = None
    narrative: str = ""
    observer_count: Optional[int] = 1
    url: Optional[str] = None
    possible_abduction: bool = False
    missing_time: bool = False
    marks_on_body: bool = False
    landed: bool = False
    lights_on_object: bool = False
    animals_reacted: bool = False

    @field_validator("id", mode="before")
    @classmethod
    def _coerce_id(cls, v):
        # Sighting ids arrive as ints/strings; the rest of the pipeline keys on strings.
        return str(v) if v is not None else v


class ChunkMetadata(BaseModel):
    """Pinecone-bound metadata for a chunk (no nulls are sent; the client drops None)."""
    model_config = {"extra": "allow"}

    occurred: Optional[str] = None
    location: Optional[str] = None
    shape: Optional[str] = None
    shape_lc: Optional[str] = None
    observer_count: Optional[int] = None
    url: Optional[str] = None
    possible_abduction: bool = False
    missing_time: bool = False
    marks_on_body: bool = False
    landed: bool = False
    lights_on_object: bool = False
    animals_reacted: bool = False


class Chunk(BaseModel):
    """One embeddable chunk, as emitted by chunk_and_enrich.py."""
    model_config = {"extra": "allow"}

    chunk_id: str
    source_report_id: str
    source: Optional[str] = None
    chunk_text: str
    metadata: ChunkMetadata
    entities: List[Any] = []
    effects: List[str] = []
    sequence: List[str] = []

    @field_validator("chunk_text")
    @classmethod
    def _nonempty_text(cls, v):
        if not v or not v.strip():
            raise ValueError("chunk_text must be non-empty (an empty chunk embeds to noise)")
        return v


def validate_report(d: dict) -> Report:
    """Raises pydantic.ValidationError on drift."""
    return Report(**d)


def validate_chunk(d: dict) -> Chunk:
    """Raises pydantic.ValidationError on drift."""
    return Chunk(**d)


def report_is_valid(d: dict):
    """Non-raising boundary check -> (ok: bool, error: str|None)."""
    try:
        validate_report(d)
        return True, None
    except ValidationError as e:
        return False, str(e)


def chunk_is_valid(d: dict):
    """Non-raising boundary check -> (ok: bool, error: str|None)."""
    try:
        validate_chunk(d)
        return True, None
    except ValidationError as e:
        return False, str(e)
