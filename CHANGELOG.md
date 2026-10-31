# Changelog

## v0.1.0 (2026-10-30)

- Evidence-passport seal over the membrane-arena small benchmark:
  deterministic manifest + SHA-256 artifacts + fail-closed verify.
- Bar MET on the fixture benchmark: seal verifies and sealed numbers
  match benchmark.json byte-for-byte (13,685 bytes; 4 scopes, 96 metrics).
- Tests: round-trip, one-byte tamper failure, determinism, fail-closed
  malformed/duplicate/NaN input, unsigned-bundle refusal, wrong-digest
  manifest refusal (7 tests).
