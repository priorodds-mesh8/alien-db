"""UAP corpus utilities: Pinecone client (real client embeddings + vector search), embedder, events, benchmarks, cost, glass-box traces."""
from .pinecone_client import PineconeClient
from .events import write_event, new_run_id
from .fixtures.uap_benchmark import get_benchmark_records, UAP_BENCHMARK_RECORDS
from .cost_meter import CostMeter, GLOBAL_METER
from .fabrication import fabrication_eval, build_shape_filter
from .schema import (
    Report, Chunk, ChunkMetadata,
    validate_report, validate_chunk, report_is_valid, chunk_is_valid,
)

__all__ = ["PineconeClient", "write_event", "new_run_id", "get_benchmark_records", "UAP_BENCHMARK_RECORDS", "CostMeter", "GLOBAL_METER", "fabrication_eval", "build_shape_filter", "Report", "Chunk", "ChunkMetadata", "validate_report", "validate_chunk", "report_is_valid", "chunk_is_valid"]
