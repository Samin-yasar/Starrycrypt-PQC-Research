# Changelog

All notable changes to this project will be documented in this file.

## [2.0.2] - 2026-07-20

### Added
- Module-level docstrings for all Python analysis scripts (`statistical_tests.py`,
  `generate_figures.py`, `statistical_power_analysis.py`,
  `revision_analysis_corrected.py`, `scripts/verify_data.py`,
  `scripts/explore_data.py`) documenting purpose, inputs, outputs, outlier
  policy, dependencies, and bibliographic references.
- Per-function docstrings (Google style) for all public Python functions across
  the analysis pipeline, including `load_data`, `cohen_d`, `calculate_power`,
  `calculate_required_n`, `ci95`, `welch_ttest`, `stats`, `to_float`,
  `categorize_engine`, `save`, `find_data_file`, and all eight `fig*` generators.
- Comprehensive Doxygen-style comments for all C source files:
  - `kem.c`        — KEM public API (KeyGen, Encaps, Decaps) with FIPS 203 §6 cross-references
  - `indcpa.c`     — IND-CPA encryption/decryption internals with NTT pipeline diagram
  - `randombytes.c` — CSPRNG strategy (WASM `getRandomValues`, fallback), entropy hazards
  - `reduce.c`     — Montgomery and Barrett reduction with full algebraic derivation
  - `verify.c`     — Constant-time memory comparison with side-channel rationale
  - `benchmark_api.c` — Timing-isolated benchmark WASM exports
  - `params.h`     — FIPS 203 §4 parameter derivation with algebraic context
  - `api.h`        — Public KEM API contract with size guarantees
- Full JSDoc coverage for `mlkem768-wrapper.js`:
  - Module-level architecture diagram (WASM loading, hybrid KEM design, memory safety, benchmarking)
  - All private helpers: `_malloc`, `_free`, `_zeroize`, `heapWrite`, `heapRead`
  - All exported KEM functions: `loadModule`, `mlkemKeyGen`, `mlkemEncaps`, `mlkemDecaps`
  - Cryptographic primitives: `hkdfSha256`, `aesGcmEncrypt`, `aesGcmDecrypt`, `deriveSessionKey`
  - Benchmark entry point: `runHandshake` with full return-type documentation
- Full JSDoc coverage for `purejs-wrapper.js`:
  - Module-level docstring explaining API compatibility and design rationale vs. WASM variant
  - All functions including `loadModule` (no-op rationale), `mlkemEncaps`, `mlkemDecaps`,
    `checkX25519Support`, `x25519KeyGen`, `x25519Derive`, `hkdfSha256`, `aesGcmEncrypt`,
    `aesGcmDecrypt`, `deriveSessionKey`, `runHandshake`
- Full JSDoc coverage for `telemetry.js`:
  - Module-level docstring documenting architecture, privacy policy, and deprecation note
  - `uploadBenchmark` with full parameter and return-value documentation
  - `uploadBenchmarkDirect` marked `@deprecated` with migration guidance
- Professional `Makefile` with:
  - Section headers for WASM build, dev server, cleanup, and paper build phases
  - Inline comments on every flag in `EMFLAGS` (`-O3`, `WASM=1`, `MODULARIZE`, etc.)
  - Documented `EXPORTS` allowlist and `RT_METHODS` (Emscripten runtime helpers)
  - LaTeX four-pass compilation sequence explained
- Professional `CONTRIBUTING.md` with ten structured sections: project scope,
  issue reporting matrix, development setup (prerequisites table, build steps),
  branching/PR workflow, language-specific code style guides (C, JS, Python, Markdown),
  PR checklist, contribution opportunity table, security disclosure procedure,
  Conventional Commits convention with examples, and license agreement.

### Changed
- `kem.h` documentation upgraded with Doxygen `@file`, `@brief`, `@param`, `@return`
  annotations and FIPS 203 §6 cross-references.
- `wasm_export.c` file header rewritten with architecture overview, security
  contract, and per-function documentation for all six exported WASM symbols.
- `CONTRIBUTING.md` fully rewritten to professional research-artifact standard.

## [2.0.1] - 2026-05-10

### Changed
- Artifact restructured as independent release submodule
- Rewrote `verification_report.md` into formal **Data Integrity and Statistical Verification Report**
  - Documented two statistical corrections with mathematical rationale
  - Added reproducibility instructions and formal limitations disclosure
- Removed outdated `data_verification_report.md` (referenced stale N=464 dataset)
- Removed redundant analysis scripts:
  - `analysis/temp_check.py` – `temp_check4.py` (throwaway debug scripts)
  - `analysis/_get_stats.py` (referenced stale 2026-05-03 CSV)
  - `analyze_data_simple.py` (referenced stale 2026-05-03 CSV)
  - `analysis/revision_analysis.py` (superseded by `revision_analysis_corrected.py` and `revision_analysis_stdlib.py`)
- Renamed `run/` → `benchmark/` for clarity; removed stale duplicate `benchmark/` directory
- Reorganized Python scripts into professional structure:
  - `scripts/verify_data.py` — canonical stdlib-only verification (from `verify_data_pure.py`)
  - `scripts/explore_data.py` — pandas-based data exploration (from `analyze_data.py`)
  - `scripts/archive/verify_data_legacy.py` — deprecated audit against old dataset
  - `analysis/statistical_tests.py` — Welch's t-test, Cohen's d, CI computation (from `analysis/verify_stats.py`)
  - Standardized all data paths to `performance_data/...` (relative to repo root)
- Date corrections: internal report timestamps aligned to release date (2026-05-06 → 2026-05-10)

### Fixed
- Canonical statistics now consistently reflect N=462 policy (240 WASM, 223 JS)
- Safari non-SIMD median corrected from 0.72 ms to 0.49 ms
- Chrome 87 outlier formally documented with exclusion rationale
- Median vs. mean robustness properly explained

## [2.0.0] - 2026-05-10

### Added
- Complete ML-KEM-768 (FIPS 203) implementation
- Hybrid key exchange: ML-KEM-768 + X25519 with HKDF-SHA-256
- WebAssembly (WASM) optimized build
- Pure JavaScript implementation for comparison
- Browser-native constant-time testing harness (Welch's t-test)
- Comprehensive telemetry system for performance benchmarking
- 462-session benchmark dataset across 22 hardware configurations
- 8 publication-quality figures
- IACR ePrint submission ready

### Performance
- WASM achieves 3.45× observed latency reduction over pure JavaScript (2.34ms vs 8.07ms, outlier excluded)
- SIMD-capable browsers: 2.38ms mean latency
- Mobile devices achieve sub-2.5ms latency with modern browsers

### Security
- Constant-time Barrett reduction
- Secure memory zeroization via WASM
- FIPS 203 compliant domain separation

## [1.0.0] - 2024 (Pre-release)

### Added
- Initial ML-KEM implementation (Kyber Round 3)
- Basic WASM compilation
- Simple benchmarking harness

### Changed
- Migrated from Kyber Round 3 to FIPS 203 final standard

## Future Roadmap

### Planned
- [ ] SIMD128 intrinsics for WASM build
- [ ] Web Workers support for multi-threading
- [ ] Streaming API for large data
- [ ] Additional statistical visualizations
- [ ] Formal verification of constant-time properties

### Under Consideration
- [ ] ML-KEM-512 and ML-KEM-1024 variants
- [ ] ML-DSA (FIPS 204) signature support
- [ ] Integration with Web Crypto API polyfill

---

Format based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)
