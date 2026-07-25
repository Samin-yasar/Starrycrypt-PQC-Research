git clone https://github.com/Samin-yasar/starrycrypt-pqc.git
# StarryCrypt-PQC — Release Artifacts (Clean)

This directory contains the curated research artifact for the StarryCrypt-PQC study: a minimal, well-documented set of source, analysis, and publication materials needed to reproduce the paper and verify results.

Keep this folder under version control. Large generated build artifacts and experimental dashboards have been removed to keep the release focused on source, data, and documentation.

Highlights
- Research code: `src/`, `analysis/`, `scripts/`
- Paper source and figures: `paper/`
- Documentation: `docs/`, `CHANGELOG.md`, `CONTRIBUTING.md`
- Data: `performance_data/` (canonical telemetry CSV)

Repository layout (essential)

- `src/` — source code for the implementation and JS wrapper
- `analysis/` — Python analysis scripts and figure generation
- `paper/` — LaTeX source, figures, and bibliography
- `docs/` — reference docs (API, architecture, security)
- `scripts/` — helper scripts for verification and exploration
- `performance_data/` — canonical telemetry dataset used in paper
- `verification_report.md` — formal data integrity report
- `CHANGELOG.md`, `CONTRIBUTING.md`, `LICENSE`, `Makefile`

Quick reproduction

1. Create a Python virtualenv and install analysis deps:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r ../requirements.txt
```

2. Reproduce figures from the committed dataset:

```bash
cd analysis
python3 generate_figures.py
```

3. Build WASM artifacts (optional, requires Emscripten):

```bash
make all
```

Notes
- Committed build artifacts (previously under `dist/`) were intentionally removed from this directory to keep the release lean. Use `make all` to rebuild locally.
- The removed preview dashboards and benchmark HTML files are archived in the project history; see the git tags for older snapshots.

Citation
Please cite the paper when using the dataset or analysis: see `paper/references.bib` and `CHANGELOG.md`.

License
This release is licensed under the Apache 2.0 License (see `LICENSE`).

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
