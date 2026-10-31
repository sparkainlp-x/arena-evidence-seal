"""Verify a sealed arena benchmark bundle. Fail-closed, exit 2 on any failure.

Verification is three checks, all of which must pass:
1. The bundle manifest validates under the vendored evidence-passport
   validator (strict schema, duplicate-key and non-finite rejection,
   SHA-256 of every listed artifact recomputed and compared). A missing
   manifest means the input was never sealed ("unsigned") and fails here.
2. The bundled benchmark.json bytes hash to the digest recorded in the
   manifest (already enforced by check 1, reported explicitly).
3. When a source benchmark path is given, the bundled benchmark.json bytes
   are byte-identical to the source bytes. Any difference is a finding,
   never a rounding fix.

Nothing is "repaired". On failure this module reports the reason and
refuses; it never writes a sealed output.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from .passport import ManifestError, load_and_validate


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def verify_bundle(bundle_dir: Path, source_benchmark_path: Path | None = None) -> tuple[bool, str, dict[str, Any] | None]:
    """Return (ok, message, report-or-None). Never raises on bad input."""
    bundle_dir = Path(bundle_dir)
    manifest_path = bundle_dir / "manifest.json"
    if not manifest_path.is_file():
        return False, "FAIL: no manifest.json in bundle (unsigned input, never sealed)", None
    try:
        report = load_and_validate(manifest_path)
    except ManifestError as exc:
        return False, f"FAIL: manifest validation refused: {exc}", None
    except OSError as exc:
        return False, f"FAIL: cannot read bundle: {exc}", None
    sealed_path = bundle_dir / "benchmark.json"
    if not sealed_path.is_file():
        return False, "FAIL: bundle has no benchmark.json", None
    sealed_bytes = sealed_path.read_bytes()
    recorded = None
    for artifact in report["integrity"]["files"]:
        if artifact["path"] == "benchmark.json":
            recorded = artifact["expected_sha256"]
    if recorded is None:
        return False, "FAIL: manifest records no benchmark.json artifact", None
    if _sha256_bytes(sealed_bytes) != recorded:
        return False, "FAIL: sealed benchmark.json hash does not match the manifest digest", report
    if source_benchmark_path is not None:
        source_bytes = Path(source_benchmark_path).read_bytes()
        if sealed_bytes != source_bytes:
            return False, "FAIL: sealed benchmark.json bytes differ from the source benchmark JSON", report
    return True, "VALID: seal verifies and sealed numbers match the source benchmark JSON byte-for-byte", report


def main(argv: list[str] | None = None) -> int:
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Verify a sealed arena benchmark bundle (fail-closed).")
    parser.add_argument("bundle", type=Path)
    parser.add_argument("--source", type=Path, default=None, help="source benchmark.json for the byte-for-byte check")
    args = parser.parse_args(argv)
    ok, message, _report = verify_bundle(args.bundle, args.source)
    print(message, file=sys.stderr if not ok else sys.stdout)
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
