"""
Synthetic benchmark archetypes for UAP pattern scoring (modeled exactly on alertmedia-benchmark in agentic-sdr-demo).

These represent "known high-signal motifs" (e.g. gray medical exam + missing time, silent triangle hover + animal reaction).
Used for future "score_query" or similarity ranking against live queries/reports.
"""
from typing import List, Dict, Any

UAP_BENCHMARK_RECORDS: List[Dict[str, Any]] = [
    {
        "_id": "motif-gray-exam-missing-time-v1",
        "corpus_label": "synthetic_benchmark",
        "chunk_text": "Small gray beings with large black eyes performed medical examinations on a table. Subject reported missing time of 2 hours after close encounter on highway. Telepathic communication about 'the project'. Physical scar noted afterward.",
        "motif": "gray_medical_exam_missing_time",
        "entity_type": "gray",
        "procedure": "table_exam",
        "after_effect": "missing_time_scar",
        "boost_tags": "gray,exam,missing_time,highway",
        "risk_tags": "cultural_contamination",
    },
    {
        "_id": "motif-silent-triangle-hover-v1",
        "corpus_label": "synthetic_benchmark",
        "chunk_text": "Large black triangle craft with lights at corners hovered silently. No sound. Animal reactions extreme (dogs hid, cattle panicked). Instant vertical acceleration on departure. Physiological pressure in head during sighting.",
        "motif": "silent_triangle_hover_animal_reaction",
        "entity_type": "craft_triangle",
        "procedure": "hover_scan",
        "after_effect": "head_pressure_animal_distress",
        "boost_tags": "triangle,silent,hover,animal",
        "risk_tags": "",
    },
    {
        "_id": "motif-disk-beam-livestock-v1",
        "corpus_label": "synthetic_benchmark",
        "chunk_text": "Metallic disk with dome hovered over barn. Emitted beam of light that scanned livestock. Animals froze in place. Object departed at extreme speed with no sonic boom. Interference on camera/phone.",
        "motif": "disk_beam_livestock",
        "entity_type": "craft_disk",
        "procedure": "beam_scan",
        "after_effect": "animal_freeze_electronic_interference",
        "boost_tags": "disk,beam,livestock",
        "risk_tags": "",
    },
]

def get_benchmark_records() -> List[Dict[str, Any]]:
    return UAP_BENCHMARK_RECORDS
