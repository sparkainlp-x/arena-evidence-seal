# arena-evidence-seal v0.1.0

Evidence-passport seal over an arena benchmark: feed the membrane-arena
small benchmark JSON through the evidence-passport fail-closed mechanism,
producing a sealed bundle plus a verify command.

## What "seal" means here

The evidence-passport mechanism (vendored unchanged in
`src/arena_evidence_seal/passport.py`) is a strict manifest validator, not
a signature scheme: a fixed manifest schema, rejection of duplicate JSON
keys and non-finite numbers, safe relative artifact paths, and SHA-256
verification of every listed artifact (exactly one artifact must carry
role `protocol`, and `protocol.sha256` must equal that artifact's
verified hash). A bundle that fails any of this is refused, never sealed.

So a sealed bundle is a directory with three files:

- `benchmark.json` — a byte-copy of the source benchmark output.
- `benchmark.py` — a byte-copy of the benchmark script (the protocol artifact).
- `manifest.json` — built deterministically (sorted keys, no timestamps):
  project/dataset/code/protocol fields, the benchmark's `sweep` table
  transcribed as metrics (every finite number, nothing computed or
  rounded), and SHA-256 digests of both artifacts.

Verification re-validates the manifest fail-closed, re-hashes the bundled
files, and byte-compares the bundled benchmark against the source.
Any mismatch fails. Nothing is repaired.

## Bar (preregistered) and measured outcome

Bar: the seal verifies AND the sealed numbers match the benchmark JSON
byte-for-byte. Any mismatch would be a finding, not a rounding fix.

Measured on the fixture benchmark (the real
`membrane-arena-3x3-upgrade` small benchmark: seeds 0–4, steps 200,
coupling 0.02, dt 0.01/0.05, legacy/exact modes):

- **Bar MET.** `verify` reports VALID: seal verifies and sealed numbers
  match the source benchmark JSON byte-for-byte.
- `benchmark.json`: 13,685 bytes, SHA-256
  `a09ef2e00e179094fa3b6ad24be034ecc8440cb6759b06d6fdba1899040c757b`.
- `benchmark.py`: 8,855 bytes, SHA-256
  `2394ebaeff66ff6d0ee8fd929f8cb33d4feff687174dcfa046eb3bc29c182f45`.
- Manifest: 4 scopes (one per sweep config), 96 metrics transcribed from
  the benchmark's own `sweep` table.
- Tamper: changing one digit byte in the sealed benchmark makes
  verification FAIL.
- Determinism: sealing twice produces byte-identical bundles.
- Fail-closed: malformed JSON, duplicate keys, and NaN inputs are refused
  (never sealed); a bundle directory with benchmark data but no manifest
  ("unsigned") is refused; a manifest with an edited digest is refused.

## Run it

```sh
python3 demo.py            # seal the fixture benchmark, then verify it
python3 tests/tests.py     # 7 tests, from the package root
```

The verify command is also usable directly:

```sh
python3 -m arena_evidence_seal.verify <bundle-dir> --source <benchmark.json>
```

(run from `src/`, or import `verify_bundle` from the package).

## Honest limits

- SHA-256 matching proves byte-for-byte consistency between a referenced
  file and the digest recorded in the bundle. It does NOT prove
  authorship, when a file or protocol existed, provenance authenticity,
  or measurement or method validity (evidence-passport's own disclaimer,
  carried in the manifest report).
- Classical synthetic toy only. No quantum-hardware, medical, brain, or
  consciousness claim.
- This package does not re-run the arena and does not re-derive the
  numbers. The sealed numbers are the benchmark's own outputs, copied
  byte-for-byte.
- `runs.csv` from the same benchmark run is NOT sealed here
  (benchmark.json only).
- The manifest `seed` field is null because the benchmark used seeds
  0–4, not a single seed; the seed list is stated in the dataset
  description instead of inventing a single seed.
- There is no signature and no key in this scheme. "Unsigned" in the
  tests means a bundle presented without a manifest, which verification
  refuses.

## Provenance

- `src/arena_evidence_seal/passport.py` is vendored UNCHANGED from
  `sparkainlp-x/evidence-passport`, file `evidence_passport.py`
  (TOOL_VERSION 0.1.1, read 2026-10-30). The adapter (`seal.py`,
  `verify.py`) is new code written for this package and uses the
  vendored validator; it does not reimplement or weaken it.
- `fixtures/benchmark.json` and `fixtures/benchmark.py` are byte-copies
  of `membrane-arena-3x3-upgrade/benchmark_results_small/benchmark.json`
  and `scripts/benchmark.py`. The benchmark script itself writes no
  timestamps, which is what makes the sealed bundle deterministic.

## Licence

AGPL-3.0-only. See `LICENSE`.
