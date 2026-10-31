"""Seal an arena benchmark JSON through the evidence-passport mechanism.

The "seal" here is exactly the evidence-passport fail-closed mechanism,
vendored unchanged in passport.py: a strict manifest schema plus SHA-256
artifact verification. There is no signature and no key: "sealed" means a
manifest was built deterministically from the benchmark bytes, the bundle
validates fail-closed, and the sealed benchmark copy is byte-identical to
the source. SHA-256 matching proves byte-consistency only. It does not
prove authorship, timing, provenance authenticity, or measurement validity
(evidence-passport's own disclaimer, carried in the manifest report).

Determinism: the manifest contains no timestamps and no wall-clock
fields. The same benchmark + protocol bytes always produce the same
manifest bytes.
"""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any

from .passport import ManifestError, load_and_validate, read_json

RUN_ID = "arena-evidence-seal-benchmark"


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _unit_for(field: str) -> str:
    if "fraction" in field:
        return "fraction"
    if "steps" in field:
        return "steps"
    return "value"


def build_manifest(benchmark: dict[str, Any], benchmark_sha: str, protocol_sha: str) -> dict[str, Any]:
    """Build the evidence-passport manifest for a parsed benchmark dict.

    Metrics are transcribed ONLY from the benchmark's own ``sweep`` table:
    every finite number there becomes one metric. Nothing is computed,
    rounded, or invented here. The sealed numbers themselves are the
    byte-copy of benchmark.json, not this transcription.
    """
    if not isinstance(benchmark, dict):
        raise ManifestError("benchmark JSON must be an object")
    sweep = benchmark.get("sweep")
    if not isinstance(sweep, dict) or not sweep:
        raise ManifestError("benchmark JSON has no non-empty 'sweep' table")
    seeds = benchmark.get("seeds")
    seed_note = f"seeds {seeds}" if isinstance(seeds, list) else "seeds not recorded"
    steps = benchmark.get("steps")
    steps_note = f"steps {steps}" if isinstance(steps, int) else "steps not recorded"

    rows: list[dict[str, Any]] = []
    for config in sorted(sweep.keys()):
        table = sweep[config]
        if not isinstance(table, dict):
            raise ManifestError(f"sweep entry {config!r} is not an object")
        metrics: list[dict[str, Any]] = []
        for field in sorted(table.keys()):
            value = table[field]
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                continue
            if not math.isfinite(float(value)):
                raise ManifestError(f"sweep metric {config} / {field} is not finite")
            metrics.append({"name": field, "value": value, "unit": _unit_for(field)})
        if not metrics:
            raise ManifestError(f"sweep entry {config!r} has no finite numeric metrics")
        rows.append({"scope": config, "method": "membrane-arena-3x3-upgrade benchmark.py", "metrics": metrics})

    return {
        "schema_version": 1,
        "run_id": RUN_ID,
        "project": {
            "name": "membrane-arena-3x3 benchmark",
            "version": "benchmark_results_small",
            "source_url": None,
            "source_note": (
                "Local deterministic output of membrane-arena-3x3-upgrade "
                "scripts/benchmark.py (seeds 0-4, steps 200, coupling 0.02, "
                "dt 0.01/0.05, legacy/exact modes). No public URL claimed."
            ),
        },
        "evidence_class": "synthetic",
        "dataset": {
            "name": "arena benchmark (small)",
            "kind": "synthetic benchmark output",
            "description": (
                "Survival curves (201 points x 4 configs) and sweep summaries "
                f"from the deterministic small benchmark; {seed_note}, {steps_note}."
            ),
            "source_url": None,
        },
        "code": {"version": "membrane-arena-3x3-upgrade (local tree)", "commit": None},
        "seed": None,
        "protocol": {
            "name": "benchmark.py",
            "version": "small benchmark (seeds 0-4)",
            "sha256": protocol_sha,
            "locked_at": "deterministic run, no timestamp recorded",
            "lock_commit": None,
            "description": (
                "The benchmark script whose bytes are hashed as the protocol "
                "artifact. The script itself writes no timestamps."
            ),
        },
        "baselines": ["legacy operator mode", "exact operator mode"],
        "results": rows,
        "result_label": "descriptive_only",
        "interpretation": (
            "Sealed bundle for the small arena benchmark: the manifest records "
            "SHA-256 digests of benchmark.json and benchmark.py, and the bundle "
            "carries byte-copies of both. Verification proves the sealed "
            "benchmark copy is byte-identical to the source and the bundle is "
            "internally consistent. It does not prove authorship, timing, "
            "provenance authenticity, or measurement validity."
        ),
        "limitations": [
            "SHA-256 matching proves byte-consistency only (see evidence-passport disclaimer).",
            "Synthetic toy benchmark; no quantum-hardware, medical, brain, or consciousness claim.",
            "Sealed numbers are the benchmark's own outputs, copied byte-for-byte; this package does not re-run the arena or re-derive the numbers.",
            "runs.csv from the same benchmark run is NOT sealed in this bundle (benchmark.json only).",
            "The manifest seed field is null because the benchmark used seeds 0-4, not a single seed; the seed list is stated in the dataset description.",
        ],
        "artifacts": [
            {
                "path": "benchmark.py",
                "role": "protocol",
                "description": "Benchmark script, hashed as the protocol artifact.",
                "sha256": protocol_sha,
            },
            {
                "path": "benchmark.json",
                "role": "benchmark-data",
                "description": "Benchmark output JSON, sealed byte-for-byte.",
                "sha256": benchmark_sha,
            },
        ],
    }


def seal(benchmark_json_path: Path, protocol_py_path: Path, out_dir: Path) -> dict[str, Any]:
    """Seal a benchmark JSON into out_dir. Returns the manifest dict.

    Refuses (raises ManifestError, never writes a sealed bundle) when the
    benchmark JSON is malformed, has duplicate keys, or contains
    non-finite numbers, or when either input file is unreadable.
    """
    benchmark_json_path = Path(benchmark_json_path)
    protocol_py_path = Path(protocol_py_path)
    out_dir = Path(out_dir)
    # Fail-closed input read: duplicate keys and non-finite constants raise.
    benchmark = read_json(benchmark_json_path)
    benchmark_sha = _sha256_file(benchmark_json_path)
    protocol_sha = _sha256_file(protocol_py_path)
    manifest = build_manifest(benchmark, benchmark_sha, protocol_sha)
    # Validate the manifest we just built before writing anything: if it
    # does not pass the vendored validator, there is no sealed bundle.
    # (Validation needs the artifacts beside the manifest, so write to a
    # staging layout first, validate, then keep it only on success.)
    out_dir.mkdir(parents=True, exist_ok=True)
    sealed_json = out_dir / "benchmark.json"
    sealed_py = out_dir / "benchmark.py"
    manifest_path = out_dir / "manifest.json"
    sealed_json.write_bytes(benchmark_json_path.read_bytes())
    sealed_py.write_bytes(protocol_py_path.read_bytes())
    manifest_text = json.dumps(manifest, sort_keys=True, indent=2, allow_nan=False) + "\n"
    manifest_path.write_text(manifest_text, encoding="utf-8")
    try:
        load_and_validate(manifest_path)
    except ManifestError:
        sealed_json.unlink(missing_ok=True)
        sealed_py.unlink(missing_ok=True)
        manifest_path.unlink(missing_ok=True)
        raise
    return manifest
