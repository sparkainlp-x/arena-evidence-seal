"""Demo: seal the fixture benchmark, then verify it. Run: python3 demo.py."""

import hashlib
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from arena_evidence_seal.seal import seal
from arena_evidence_seal.verify import verify_bundle

ROOT = Path(__file__).resolve().parent


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    fixture_json = ROOT / "fixtures" / "benchmark.json"
    fixture_py = ROOT / "fixtures" / "benchmark.py"
    with tempfile.TemporaryDirectory() as tmp:
        bundle = Path(tmp) / "sealed"
        manifest = seal(fixture_json, fixture_py, bundle)
        metric_count = sum(len(row["metrics"]) for row in manifest["results"])
        print(f"benchmark.json sha256: {_sha(fixture_json)}")
        print(f"benchmark.py   sha256: {_sha(fixture_py)}")
        print(f"manifest scopes: {len(manifest['results'])}, metrics: {metric_count}")
        print(f"sealed benchmark bytes: {(bundle / 'benchmark.json').stat().st_size}")
        ok, message, _report = verify_bundle(bundle, fixture_json)
        print(message)
        return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
