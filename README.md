# StarryCrypt-PQC

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.20111815.svg)](https://doi.org/10.5281/zenodo.20111815)
[![WASM](https://img.shields.io/badge/WebAssembly-%E2%9C%93-654FF0)](https://webassembly.org/)
[![FIPS 203](https://img.shields.io/badge/FIPS%20203-Compliant-green)](https://csrc.nist.gov/projects/post-quantum-cryptography)
[![Version](https://img.shields.io/badge/version-v2.0.1-informational)](CHANGELOG.md)

**Evaluating Web-Based Post-Quantum Cryptography: A Statistical Analysis of ML-KEM-768 in Controlled Browser Environments**

This repository contains the complete research artifact for the paper *"Evaluating Web-Based Post-Quantum Cryptography: A Statistical Analysis of ML-KEM-768 in Controlled Browser Environments"* ([SSRN preprint](https://ssrn.com/abstract=6744539), May 2026). It includes the full ML-KEM-768 WebAssembly implementation, benchmarking harness, telemetry dataset, statistical analysis pipeline, and LaTeX paper source.

---

## Table of Contents

1. [Overview](#overview)
2. [Key Findings](#key-findings)
3. [Quick Start](#quick-start)
4. [Repository Structure](#repository-structure)
5. [Building from Source](#building-from-source)
6. [Running Benchmarks](#running-benchmarks)
7. [Reproducing Paper Results](#reproducing-paper-results)
8. [API Usage](#api-usage)
9. [Constant-Time Testing](#constant-time-testing)
10. [Performance Results](#performance-results)
11. [FIPS 203 Compliance](#fips-203-compliance)
12. [Hybrid Key Exchange](#hybrid-key-exchange)
13. [Security Considerations](#security-considerations)
14. [Browser Compatibility](#browser-compatibility)
15. [Dataset Description](#dataset-description)
16. [Citation](#citation)
17. [License](#license)
18. [Acknowledgments](#acknowledgments)

---

## Overview

StarryCrypt-PQC implements **ML-KEM-768** (NIST FIPS 203) with **X25519 hybrid key exchange** targeting web browsers. Two independent implementations are provided to enable rigorous comparative benchmarking:

- **WebAssembly (WASM)**: C source compiled via Emscripten. Recommended for performance-sensitive deployments.
- **Pure JavaScript**: Backed by `@noble/post-quantum` (v0.6.1). Provides a portable comparison baseline without requiring WASM compilation.

Both share an identical async JavaScript API and produce byte-for-byte compatible output.

### Key Features

- **FIPS 203 Compliant**: NIST-standardized ML-KEM-768 implementation derived from the PQClean reference library.
- **Hybrid Key Exchange**: ML-KEM-768 + X25519 combined via HKDF-SHA-256, following [draft-ietf-tls-ecdhe-mlkem-04](https://datatracker.ietf.org/doc/draft-ietf-tls-ecdhe-mlkem-04/).
- **3.45x Observed Speedup**: WASM delivers 3.45x lower mean handshake latency over pure JavaScript (2.34 ms vs. 8.07 ms; p < 0.0001, Welch's t-test).
- **Statistical Rigor**: 462 benchmark sessions across 22 hardware configurations and 3 browser engines.
- **Constant-Time Screening**: Browser-native Welch's t-test harness for Fujisaki-Okamoto rejection-path timing.
- **Cross-Platform**: Validated on WebKit (Safari), Blink (Chrome/Edge/Brave), and Gecko (Firefox).

---

## Key Findings

| Metric | Value |
|---|---|
| WASM mean latency | 2.34 ms (n = 239, Chrome 87 excluded) |
| Pure JS mean latency | 8.07 ms (n = 223) |
| Observed speedup | 3.45x (means ratio) |
| Statistical significance | p < 0.0001, Welch's t-test; survives Bonferroni correction |
| Effect size | Cohen's d = 0.77 (large) |
| Uninstrumented overhead | ~87% of total handshake latency |
| Cryptographic core speedup (estimated) | 7–9x (not directly measured) |

**Important caveat**: Approximately 87% of the measured handshake latency is uninstrumented framework overhead (WASM instantiation, JS garbage collection, JS/WASM boundary crossing). The 3.45x figure reflects total handshake time, not isolated cryptographic core performance.

---

## Quick Start

### Prerequisites

| Tool | Version | Purpose |
|---|---|---|
| [Emscripten](https://emscripten.org/) | Latest stable | WASM compilation |
| Modern browser | Chrome 57+, Firefox 52+, Safari 11+ | Benchmark execution |
| Python | 3.8+ | Data analysis and figure generation |
| Node.js | 18+ | Optional, for JS tooling |

### Installation

```bash
# Clone the repository
git clone https://github.com/Samin-yasar/starrycrypt-pqc.git
cd starrycrypt-pqc

# Build the WASM module (requires Emscripten on PATH)
make all

# Start local development server
make serve
# Open http://localhost:8080/benchmark/ in your target browser
```

---

## Repository Structure

```
starrycrypt-pqc/
├── src/
│   ├── wasm/                    # C source for WASM compilation (PQClean-derived)
│   │   ├── kem.c                # ML-KEM-768 key encapsulation mechanism
│   │   ├── indcpa.c             # IND-CPA secure public-key encryption layer
│   │   ├── poly.c               # Polynomial arithmetic over R_q = Z_q[X]/(X^256 + 1)
│   │   ├── polyvec.c            # Length-k vectors of polynomials
│   │   ├── ntt.c                # Number Theoretic Transform (NTT) and inverse
│   │   ├── fips202.c            # SHA-3 family and SHAKE XOF (FIPS 202)
│   │   ├── cbd.c                # Centered binomial distribution sampling
│   │   ├── reduce.c             # Barrett reduction modulo q=3329
│   │   ├── verify.c             # Constant-time comparison and conditional copy
│   │   ├── randombytes.c        # WASM-compatible CSPRNG (delegates to JS)
│   │   ├── symmetric-shake.c    # SHAKE-based symmetric primitive glue
│   │   ├── wasm_export.c        # Emscripten KEEPALIVE export wrappers
│   │   ├── benchmark_api.c      # Per-function timing exports for benchmarks
│   │   ├── params.h             # ML-KEM-768 parameter set (K=3, q=3329, n=256)
│   │   └── api.h                # Public C API (PQCLEAN_MLKEM768_CLEAN_*)
│   └── js/
│       ├── mlkem768-wrapper.js  # WASM module loader, memory management, hybrid KEx
│       ├── purejs-wrapper.js    # @noble/post-quantum pure JS backend (same API)
│       └── telemetry.js         # Supabase telemetry upload (deprecated, kept for reference)
├── dist/
│   ├── mlkem768.js              # Emscripten-generated JS loader (committed artifact)
│   └── mlkem768.wasm            # Compiled WASM binary (committed artifact)
├── benchmark/
│   ├── index.html               # WASM benchmark harness
│   └── pure-js.html             # Pure JS benchmark harness
├── dashboard/
│   └── index.html               # Offline results visualization dashboard
├── performance_data/
│   └── starrycrypt_telemetry_2026-05-05.csv   # Complete 462-session dataset
├── analysis/
│   ├── generate_figures.py      # Reproduces all 8 publication figures
│   ├── statistical_tests.py     # Welch's t-test, Cohen's d, confidence intervals
│   ├── revision_analysis_corrected.py  # Corrected subgroup analysis (v2.0.1)
│   ├── revision_analysis_stdlib.py     # stdlib-only subgroup analysis
│   ├── statistical_power_analysis.py   # Post-hoc power analysis
│   └── figures/                 # Generated PDF and PNG figures
├── scripts/
│   ├── verify_data.py           # Canonical stdlib-only dataset verification
│   ├── explore_data.py          # Pandas-based exploratory analysis
│   └── archive/
│       └── verify_data_legacy.py  # Deprecated: verification against N=464 dataset
├── docs/
│   ├── API.md                   # Full JavaScript API reference
│   ├── ARCHITECTURE.md          # System architecture and design rationale
│   └── SECURITY.md              # Security policy and threat model
├── paper/
│   ├── main.tex                 # LaTeX paper source
│   ├── references.bib           # BibTeX bibliography
│   ├── README.txt               # Compilation instructions
│   └── *.pdf                    # Pre-generated figures for paper build
├── src/assets/fonts/            # Self-hosted Inter and JetBrains Mono fonts
├── verification_report.md       # Formal data integrity and corrections report
├── CHANGELOG.md                 # Version history and changes
├── CONTRIBUTING.md              # Contribution guidelines
├── Makefile                     # Build automation
└── LICENSE                      # Apache License 2.0
```

---

## Building from Source

### Install Emscripten

```bash
git clone https://github.com/emscripten-core/emsdk.git
cd emsdk
./emsdk install latest
./emsdk activate latest
source ./emsdk_env.sh   # Add to your shell profile for persistence
```

### Compile the WASM Module

```bash
cd starrycrypt-pqc
make all          # Compiles src/wasm/*.c → dist/mlkem768.js + dist/mlkem768.wasm
make clean        # Removes compiled output (dist/mlkem768.js, dist/mlkem768.wasm)
```

The Makefile compiles with `-O3` optimization and exports the following functions via `EMSCRIPTEN_KEEPALIVE`:
`mlkem_malloc`, `mlkem_free`, `mlkem_zeroize`, `mlkem_keypair`, `mlkem_enc`, `mlkem_dec`, `sha3_256_wasm`, `sha3_512_wasm`, `shake256_wasm`.

---

## Running Benchmarks

### 1. Start the Local Server

```bash
make serve   # Starts python3 -m http.server on port 8080
```

### 2. Open the Benchmark Harness

| URL | Description |
|---|---|
| `http://localhost:8080/benchmark/` | WASM implementation benchmark |
| `http://localhost:8080/benchmark/pure-js.html` | Pure JavaScript benchmark |
| `http://localhost:8080/dashboard/` | Offline results dashboard |

The benchmark runs automatically on page load. Results download as a timestamped JSON file upon completion.

### 3. Collect Data

For paper-quality data collection, append `?env=LAB` to tag sessions as controlled lab runs:

```
http://localhost:8080/benchmark/?env=LAB
```

---

## Reproducing Paper Results

All figures and statistics from the paper can be reproduced from the committed telemetry dataset.

### Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install pandas matplotlib numpy scipy
```

### Generate Figures

```bash
cd analysis
python3 generate_figures.py
# Output: analysis/figures/fig{1..8}_{name}.{pdf,png}
```

Or via Makefile (requires active venv at `.venv/`):

```bash
make figures
```

### Run Statistical Tests

```bash
python3 analysis/statistical_tests.py
# Outputs: Welch's t-test, Cohen's d, 95% CI for WASM vs. pure JS
```

### Verify Dataset Integrity

```bash
# Canonical stdlib-only verification (no external dependencies)
python3 scripts/verify_data.py

# Pandas-based exploratory analysis
python3 scripts/explore_data.py
```

### Build the Paper PDF

```bash
make paper   # Requires pdflatex and bibtex on PATH
# Or manually:
cd paper
pdflatex main.tex && bibtex main && pdflatex main.tex && pdflatex main.tex
```

---

## API Usage

Both implementations share an identical async JavaScript API. Swap the import path to switch backends.

### WASM Implementation (Recommended)

```javascript
import {
    loadModule,
    mlkemKeyGen,
    mlkemEncaps,
    mlkemDecaps,
    deriveSessionKey,
    selfTest,
    runBenchmarkN,
    verifyConstantTimeRejection
} from './src/js/mlkem768-wrapper.js';

// 1. Load the WASM module once at startup
await loadModule('./dist/mlkem768.js');

// 2. Sanity-check the implementation before benchmarking
const test = await selfTest();
console.assert(test.passed, 'Self-test failed:', test.checks);

// 3. Key generation (Alice)
const { pk, sk } = await mlkemKeyGen();
// pk: Uint8Array (1184 bytes), sk: Uint8Array (2400 bytes)

// 4. Encapsulation (Bob receives pk)
const { ct, ss: ssBob } = await mlkemEncaps(pk);
// ct: Uint8Array (1088 bytes), ssBob: Uint8Array (32 bytes)

// 5. Decapsulation (Alice receives ct)
const { ss: ssAlice } = await mlkemDecaps(ct, sk);
// ssAlice === ssBob  =>  shared secret established

// 6. Zeroize secrets when done
sk.fill(0);
ssBob.fill(0);
ssAlice.fill(0);
```

### Pure JavaScript Implementation

```javascript
// Identical API — only the import path differs
import { mlkemKeyGen, mlkemEncaps, mlkemDecaps } from './src/js/purejs-wrapper.js';

const { pk, sk } = await mlkemKeyGen();
const { ct, ss } = await mlkemEncaps(pk);
const { ss: ssDecaps } = await mlkemDecaps(ct, sk);
```

### Hybrid Key Exchange (ML-KEM + X25519)

```javascript
import {
    loadModule,
    mlkemKeyGen, mlkemEncaps, mlkemDecaps,
    x25519KeyGen, x25519Derive,
    deriveSessionKey,
    aesGcmEncrypt, aesGcmDecrypt
} from './src/js/mlkem768-wrapper.js';

await loadModule();

// --- Alice ---
const aliceMlkem = await mlkemKeyGen();
const aliceX25519 = await x25519KeyGen();

// --- Bob (receives aliceMlkem.pk and aliceX25519.publicKey) ---
const bobX25519 = await x25519KeyGen();
const { ct, ss: mlkemSSBob } = await mlkemEncaps(aliceMlkem.pk);
const x25519SSBob = await x25519Derive(bobX25519.privateKey, aliceX25519.publicKey);
const bobSessionKey = await deriveSessionKey(mlkemSSBob, x25519SSBob);

// --- Alice (receives ct and bobX25519.publicKey) ---
const { ss: mlkemSSAlice } = await mlkemDecaps(ct, aliceMlkem.sk);
const x25519SSAlice = await x25519Derive(aliceX25519.privateKey, bobX25519.publicKey);
const aliceSessionKey = await deriveSessionKey(mlkemSSAlice, x25519SSAlice);

// aliceSessionKey byte-equals bobSessionKey
```

### Benchmarking API

```javascript
import { runBenchmarkN } from './src/js/mlkem768-wrapper.js';

// n=50 timed iterations, warmup=10 untimed JIT warm-up passes
const report = await runBenchmarkN(50, 10);

console.log(report.timing.totalHandshakeMs.mean);   // e.g., 2.34
console.log(report.timing.totalHandshakeMs.p95);    // P95 latency
console.log(report.hardware);                       // browser + device metadata
```

See [`docs/API.md`](docs/API.md) for the complete API reference including all exported functions, return types, and error conditions.

---

## Constant-Time Testing

The repository includes a browser-native heuristic screening harness for the Fujisaki-Okamoto implicit-rejection path.

```javascript
import { verifyConstantTimeRejection } from './src/js/mlkem768-wrapper.js';

// n=100 interleaved trials of valid vs. 1-bit-corrupted ciphertext
const result = await verifyConstantTimeRejection(100);

console.log(`t-statistic: ${result.tStatistic}`);
console.log(`Constant-time: ${result.constantTime}`);
// result.constantTime is true when |t| < 2.0

// Full interpretation string:
console.log(result.interpretation);
```

**Scope and limitations**: This harness uses Welch's t-test (N=100) to screen for gross timing leakage in the FO rejection path. It is appropriate for development-stage screening only. Production deployment requires:

- TVLA evaluation with N >= 10,000 traces
- Hardware-level timing instrumentation (not degraded browser timers)
- A dedicated side-channel analysis framework (e.g., SCARED, LASCAR)

---

## Performance Results

### Aggregate Comparison

| Implementation | Mean Latency | Median Latency | Sessions |
|---|---|---|---|
| WASM (Chrome 87 excluded) | 2.34 ms | 1.28 ms | n = 239 |
| Pure JavaScript | 8.07 ms | 4.37 ms | n = 223 |
| **Observed speedup** | **3.45x** | **3.41x** | — |

### WASM Per-Phase Breakdown

| Operation | Mean | Description |
|---|---|---|
| KeyGen | 0.16 ms | IND-CPA key generation + FO transform |
| Encaps | 0.18 ms | IND-CPA encryption + key derivation |
| Decaps | 0.19 ms | IND-CPA decryption + implicit rejection |

### Browser Engine Comparison (WASM)

| Engine | Browsers | Mean Latency | Median Latency |
|---|---|---|---|
| Blink | Chrome, Edge, Brave | ~2.1 ms | ~1.1 ms |
| WebKit | Safari (desktop + iOS) | ~2.6 ms | ~1.3 ms |
| Gecko | Firefox | ~3.4 ms | ~1.8 ms |

---

## FIPS 203 Compliance

This implementation correctly applies all NIST-mandated modifications from Kyber Round 3 to the FIPS 203 final standard:

| Requirement | Status | Detail |
|---|---|---|
| Hash domain separation | Compliant | `0x06` suffix for SHA-3; `0x1F` for SHAKE |
| Dimension parameter concatenation | Compliant | 33-byte hash input (`seed \|\| k`) in `indcpa_keypair_derand` |
| Fujisaki-Okamoto transform | Compliant | Correct implicit rejection via `rkprf` + `cmov` |
| Constant-time comparison | Compliant | `verify.c` uses branchless XOR-accumulate |
| Entropy zeroization | Compliant | `memset(coins, 0, ...)` before stack unwind in both `keypair` and `enc` |

---

## Hybrid Key Exchange

The hybrid key exchange combines ML-KEM-768 and X25519 shared secrets following the concatenation order specified in [draft-ietf-tls-ecdhe-mlkem-04 §4.3](https://datatracker.ietf.org/doc/draft-ietf-tls-ecdhe-mlkem-04/):

```
SS_combined = HKDF-SHA-256(
    IKM  = SS_mlkem || SS_x25519,   // ML-KEM first, per draft §4.3
    salt = "" (empty),              // RFC 5869 §3.2: empty salt OK when IKM is uniform
    info = "Starrycrypt-PQC v1 | X25519MLKEM768 | AES-256-GCM",
    L    = 32 bytes
)
```

The combined secret is then used directly as an AES-256-GCM session key. The X25519 component is computed entirely inside the browser's Web Crypto API (`SubtleCrypto`); the X25519 private scalar is never exposed to JavaScript.

An all-zero X25519 shared secret (indicative of a small-order-point attack) is detected and rejected with an error, per RFC 8446 §4.2.8.

---

## Security Considerations

### Scope

This is **research code** produced for benchmarking and evaluation. It is **not intended for production deployment** without additional security review.

### Browser-Environment Constraints

| Constraint | Impact |
|---|---|
| Degraded timer resolution (100 µs – 1 ms) | Constant-time screening is limited to detecting gross leakage only |
| Non-deterministic GC pauses | Introduces tail-latency noise; mitigated by warm-up and outlier exclusion |
| JIT compilation variability | WASM offers more predictable execution than pure JS |
| Background-tab throttling | Sessions with `tabVisible = false` should be discarded from analysis |

### Memory Zeroization

WASM buffers holding secret key material and shared secrets are explicitly cleared via `mlkem_zeroize()` (a `volatile memset`) before `mlkem_free()`. JavaScript `Uint8Array` buffers holding secrets are `.fill(0)`-ed after use. Note that JIT optimization or garbage collection may retain copies beyond explicit zeroization in the JS layer.

### Constant-Time Properties

Core ML-KEM operations (NTT, Barrett reduction, FO transform) use constant-time algorithms with no secret-dependent branches. The `verify.c` module provides constant-time comparison (`verify`) and conditional copy (`cmov`, `cmov_int16`).

The JavaScript wrapper layer (type marshalling, `Uint8Array` operations, Web Crypto calls) does **not** carry constant-time guarantees.

For the full security policy and production deployment checklist, see [`docs/SECURITY.md`](docs/SECURITY.md).

---

## Browser Compatibility

| Browser | Engine | WASM | SIMD | Threads | Minimum Version |
|---|---|---|---|---|---|
| Chrome | Blink | Yes | Yes | Yes | 57+ |
| Firefox | Gecko | Yes | Yes | Yes | 52+ |
| Safari | WebKit | Yes | Yes | No | 11+ |
| Edge | Blink | Yes | Yes | Yes | 16+ |
| Brave | Blink | Yes | Yes | Yes | Current |
| Samsung Internet | Blink | Yes | Yes | Varies | 7+ |

**Note**: The committed WASM binary is compiled **without** SIMD128 intrinsics (`-msimd128`). SIMD feature detection in the benchmark reports browser SIMD capability, not whether the binary itself uses SIMD.

---

## Dataset Description

The complete telemetry dataset is committed at `performance_data/starrycrypt_telemetry_2026-05-05.csv`.

| Field | Description |
|---|---|
| `implementation` | `"wasm"` or `"pure-js"` |
| `total_handshake_mean` | Mean total handshake latency across timed runs (ms) |
| `mlkem_keygen_mean` | Mean ML-KEM KeyGen latency (ms) |
| `mlkem_encaps_mean` | Mean ML-KEM Encaps latency (ms) |
| `mlkem_decaps_mean` | Mean ML-KEM Decaps latency (ms) |
| `browser_name` | Browser name (e.g., `"Chrome"`, `"Safari"`) |
| `browser_version` | Browser version string |
| `os_name` | Operating system (e.g., `"macOS"`, `"Android"`) |
| `device_type` | `"mobile"`, `"desktop"`, or `"tablet"` |
| `device_model` | Device model; `[LAB]` prefix indicates controlled lab session |
| `wasm_simd` | Browser WASM SIMD support (`true`/`false`) |
| `wasm_threads` | Browser WASM Threads support (`true`/`false`) |
| `wasm_bulk_memory` | Browser WASM Bulk Memory support (`true`/`false`) |
| `baseline_mips` | JS-MIPS normalization score (xorshift throughput) |
| `timer_precision_ms` | Effective `performance.now()` tick granularity (ms) |
| `tab_visible` | Whether the benchmark tab was in the foreground |

**Summary statistics:**

| Metric | Value |
|---|---|
| Total sessions | 462 |
| WASM sessions | 240 |
| Pure JS sessions | 223 |
| Lab sessions | 307 (67%) |
| Field sessions | 155 (33%) |
| Hardware configurations | 22 unique (device_model, os_name) pairs |
| Browser engines | 3 (WebKit, Blink, Gecko) |

See [`verification_report.md`](verification_report.md) for a formal audit of all reported statistics, including documented corrections.

---

## Citation

If you use this code, dataset, or methodology in your research, please cite:

```bibtex
@software{yasar2026starrycrypt,
  author       = {Yasar, Samin},
  title        = {{StarryCrypt-PQC}: Web-Based {ML-KEM-768} Implementation
                  and Telemetry Dataset},
  month        = may,
  year         = {2026},
  publisher    = {Zenodo},
  version      = {v2.0.1},
  doi          = {10.5281/zenodo.20111815},
  url          = {https://doi.org/10.5281/zenodo.20111815}
}
```

The associated preprint:

```bibtex
@misc{yasar2026pqcweb,
  author       = {Yasar, Samin},
  title        = {Evaluating Web-Based Post-Quantum Cryptography:
                  A Statistical Analysis of {ML-KEM-768} in Controlled
                  Browser Environments},
  year         = {2026},
  howpublished = {SSRN Preprint},
  doi          = {10.2139/ssrn.6744539},
  url          = {https://ssrn.com/abstract=6744539}
}
```

---

## License

This project is licensed under the **Apache License 2.0**. See the [LICENSE](LICENSE) file for the full text.

The C implementation in `src/wasm/` is derived from [PQClean](https://github.com/PQClean/PQClean), which is also Apache 2.0 licensed. The pure JavaScript baseline uses [@noble/post-quantum](https://github.com/paulmillr/noble-post-quantum) (MIT licensed).

---

## Acknowledgments

- [CRYSTALS-Kyber / PQClean](https://github.com/PQClean/PQClean) — reference C implementation
- [NIST Post-Quantum Cryptography Standardization](https://csrc.nist.gov/projects/post-quantum-cryptography) — standardization process and FIPS 203
- [Emscripten](https://emscripten.org/) — C-to-WebAssembly compiler
- [@noble/post-quantum](https://github.com/paulmillr/noble-post-quantum) — audited pure JS comparison baseline
- [BrowserStack](https://www.browserstack.com/) — cross-browser lab environment for controlled sessions

---

## Contact

| Channel | Address |
|---|---|
| Research inquiries | research@samin-yasar.dev |
| Bug reports and issues | [GitHub Issues](https://github.com/Samin-yasar/starrycrypt-pqc/issues) |
| Paper | [SSRN](https://ssrn.com/abstract=6744539) |
| Dataset DOI | [10.5281/zenodo.20111815](https://doi.org/10.5281/zenodo.20111815) |

---

> **Disclaimer**: This is research code for evaluation and benchmarking purposes. While the implementation follows NIST FIPS 203 specifications and is derived from the audited PQClean reference library, production deployment requires independent security audits, TVLA-grade side-channel evaluation, and compliance review appropriate to the target threat model.
