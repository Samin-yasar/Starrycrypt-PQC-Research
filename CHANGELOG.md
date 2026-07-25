# Changelog

## [Unreleased]

### Phase 5 — Paper + Documentation (Complete)

#### Added
- Updated the paper sources in `submission/iacr/main.tex` and `submission/arxiv/main.tex` to document the Phase 4 advanced probes as operational diagnostics and to expand the limitations discussion accordingly.
- Added a dedicated advanced-probes subsection describing the sustained-load thermal benchmark and SIMD throughput probe in the benchmarking methodology.
- Recorded the Phase 5 documentation scope in the release notes so the methodology, limitations, and release narrative stay aligned.

### Phase 2 — Cold/Warm Modes + Confidence Intervals (Steps D, H)

#### Added
- **Step D — Cold/Warm Benchmark Modes**:
  - Implemented `resetModule()` and `runColdBenchmark()` exports in both wrappers.
  - Added mode selection pills (Warm Start vs Cold Start) in `run/index.html` and `run/pure-js.html` to toggle modes.
  - Implemented UI displaying a prominent Total Cold-Start Latency callout in cold mode.
  - Preserved active mode via query parameter `?mode=` when transitioning implementations.
- **Step H — In-browser 95% Confidence Intervals**:
  - Implemented standard t-interval CI computation for N >= 30, and bootstrap percentile CI fallback (1,000 resamples) for N < 30.
  - Added confidence interval display (`[95% CI: lo–hi]`) to timings lists.

### Phase 3 — Telemetry + Analysis Pipeline (Steps G, B-upload)

#### Added
- **Step G — Enriched Telemetry Schema**:
  - Created `supabase/migrations/20260623_benchmark_sessions_v3.sql` containing the `benchmark_sessions_v3` table schema and indices.
  - Created new Deno edge function `benchmark-submit-v3` in `supabase/functions/benchmark-submit-v3/index.ts` to map and store v3 telemetry data.
  - Added `uploadBenchmarkV3` in `src/js/telemetry.js` to post results to the new edge function.
- **Step B (upload) — Per-iteration JSONB upload**:
  - Uploads the full per-iteration raw timing vector array in `raw_iterations` JSONB.
- **Python Analysis Pipeline Updates**:
  - Created `analysis/fetch_v3.py` script to fetch all v3 records and export to CSV.
  - Overwrote `analysis/generate_figures.py` to support v3 CSV, filter by warm mode, use stored CI error bars (with fallback to computed), and added a new Figure 9 displaying detailed stacked phase breakdowns.
  - Recreated `analysis/statistical_tests.py` to perform Shapiro-Wilk normality, Welch t-test, and Mann-Whitney U tests.

### Phase 1 — Instrumentation Foundation (Steps A, C, B-partial)

#### Added
- **Step A — Fine-grained 12-phase timing** (`mlkem768-wrapper.js`, `purejs-wrapper.js`):
  - `runHandshake()` now measures and returns 12 distinct timing phases:
    `wasmInstantiationMs`, `mallocMs`, `mlkemKeyGenMs`, `mlkemEncapsMs`,
    `mlkemDecapsMs`, `boundaryMs`, `x25519KeyGenMs`, `x25519DeriveMs`,
    `hkdfMs`, `aesGcmEncryptMs`, `aesGcmDecryptMs`, `totalHandshakeMs`.
  - Pure JS wrapper mirrors the identical 12-phase schema for telemetry parity.

- **Step C — Time-based warm-up** (`mlkem768-wrapper.js`, `purejs-wrapper.js`):
  - Replaced fixed `warmup=100` iterations with a time-adaptive `_timeBasedWarmup()`:
    - Minimum budget: **200 ms** (matches paper §IV.A methodology).
    - Convergence criterion: CV < 5% over last 10 iterations.
    - Hard cap: **500 ms** (prevents infinite warm-up on broken engines).
    - Iteration floor: **10 iterations** (guarantees JIT tier-up on fast hardware).
  - `runBenchmarkN()` result now includes `warmupMode`, `warmupIterations`,
    and `warmupDurationMs` for reproducibility auditing.

- **Step B (partial) — Per-iteration raw timing vectors** (`mlkem768-wrapper.js`, `purejs-wrapper.js`):
  - `runBenchmarkN()` result now includes an `iterations` array: every timed
    iteration's full 12-phase timing object is preserved for post-hoc
    distribution fitting, outlier detection, and drift analysis.
  - Data volume: ~4.8 KB JSON per 50-iteration session.

- **In-browser display of all 12 phases** (`run/index.html`, `run/pure-js.html`):
  - `TIMING_LABELS` expanded to surface all 12 phases in the Timings card.
  - Phases grouped by category with inline comments: WASM-specific, ML-KEM
    lattice ops, X25519 Web Crypto, Hybrid KDF+AEAD, and end-to-end total.
  - Hardware card now shows warm-up mode, iteration count, and wall-clock duration.
  - Status bar updated to reflect time-based warm-up instead of fixed 100 iterations.

#### Changed
- `runBenchmarkN()` signature simplified: `warmup` parameter removed (now internal).
- Result schema additions: `warmupMode`, `warmupIterations`, `warmupDurationMs`, `iterations`.

#### Infrastructure
- Added `serve` script to `package.json` for local development server.
- All changes synced to `repo-release/` via `sync_release.py` (`.venv` Python).

