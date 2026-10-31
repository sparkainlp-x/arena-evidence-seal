"""Tests for arena-evidence-seal. Run from the package root: python3 tests/tests.py."""

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from arena_evidence_seal.passport import ManifestError
from arena_evidence_seal.seal import seal
from arena_evidence_seal.verify import verify_bundle

ROOT = Path(__file__).resolve().parents[1]
FIXTURE_JSON = ROOT / "fixtures" / "benchmark.json"
FIXTURE_PY = ROOT / "fixtures" / "benchmark.py"


class TestSeal(unittest.TestCase):
    def test_round_trip_real_benchmark(self):
        with tempfile.TemporaryDirectory() as tmp:
            bundle = Path(tmp) / "sealed"
            seal(FIXTURE_JSON, FIXTURE_PY, bundle)
            ok, message, report = verify_bundle(bundle, FIXTURE_JSON)
            self.assertTrue(ok, message)
            self.assertTrue(report["integrity"]["bundle_consistent"])
            self.assertEqual((bundle / "benchmark.json").read_bytes(), FIXTURE_JSON.read_bytes())
            self.assertEqual(len(report["results"]), 4)  # 4 sweep configs

    def test_tamper_one_byte_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            bundle = Path(tmp) / "sealed"
            seal(FIXTURE_JSON, FIXTURE_PY, bundle)
            data = bytearray((bundle / "benchmark.json").read_bytes())
            # Flip one digit byte inside the JSON numbers (not whitespace).
            for i, byte in enumerate(data):
                if 48 <= byte <= 57:  # ASCII digit
                    data[i] = 48 if byte != 48 else 49
                    break
            (bundle / "benchmark.json").write_bytes(bytes(data))
            ok, _message, _report = verify_bundle(bundle, FIXTURE_JSON)
            self.assertFalse(ok)

    def test_determinism(self):
        with tempfile.TemporaryDirectory() as tmp:
            first = Path(tmp) / "first"
            second = Path(tmp) / "second"
            seal(FIXTURE_JSON, FIXTURE_PY, first)
            seal(FIXTURE_JSON, FIXTURE_PY, second)
            for name in ("manifest.json", "benchmark.json", "benchmark.py"):
                self.assertEqual((first / name).read_bytes(), (second / name).read_bytes(), name)

    def test_malformed_input_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp) / "bad.json"
            bad.write_text("{not json", encoding="utf-8")
            with self.assertRaises(ManifestError):
                seal(bad, FIXTURE_PY, Path(tmp) / "out")
            dup = Path(tmp) / "dup.json"
            dup.write_text('{"a": 1, "a": 2}', encoding="utf-8")
            with self.assertRaises(ManifestError):
                seal(dup, FIXTURE_PY, Path(tmp) / "out2")
            nan = Path(tmp) / "nan.json"
            nan.write_text('{"a": NaN}', encoding="utf-8")
            with self.assertRaises(ManifestError):
                seal(nan, FIXTURE_PY, Path(tmp) / "out3")

    def test_unsigned_input_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            bundle = Path(tmp) / "unsigned"
            bundle.mkdir()
            (bundle / "benchmark.json").write_bytes(FIXTURE_JSON.read_bytes())
            ok, _message, _report = verify_bundle(bundle, FIXTURE_JSON)
            self.assertFalse(ok)

    def test_wrong_hash_manifest_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            bundle = Path(tmp) / "sealed"
            seal(FIXTURE_JSON, FIXTURE_PY, bundle)
            manifest = json.loads((bundle / "manifest.json").read_text(encoding="utf-8"))
            for artifact in manifest["artifacts"]:
                if artifact["path"] == "benchmark.json":
                    digest = artifact["sha256"]
                    artifact["sha256"] = ("0" if digest[0] != "0" else "1") + digest[1:]
            (bundle / "manifest.json").write_text(
                json.dumps(manifest, sort_keys=True, indent=2) + "\n", encoding="utf-8"
            )
            ok, _message, _report = verify_bundle(bundle, FIXTURE_JSON)
            self.assertFalse(ok)

    def test_manifest_metrics_match_sweep(self):
        source = json.loads(FIXTURE_JSON.read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as tmp:
            bundle = Path(tmp) / "sealed"
            manifest = seal(FIXTURE_JSON, FIXTURE_PY, bundle)
            by_scope = {row["scope"]: row for row in manifest["results"]}
            self.assertEqual(set(by_scope.keys()), set(source["sweep"].keys()))
            for config, table in source["sweep"].items():
                metrics = {m["name"]: m["value"] for m in by_scope[config]["metrics"]}
                for field, value in table.items():
                    if isinstance(value, (int, float)) and not isinstance(value, bool):
                        self.assertEqual(metrics[field], value, f"{config}/{field}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
