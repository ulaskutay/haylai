"""Backward-compatible shim — use pipeline.bed_ai instead."""

from pipeline.bed_ai import (  # noqa: F401
    build_prompt,
    bed_mode,
    ml_bed_enabled as musicgen_enabled,
    prefer_ml_on_gpu,
    try_generate_bed,
    warmup,
)
