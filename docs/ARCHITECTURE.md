# Architecture

This document describes the system architecture of StarryCrypt-PQC, covering the layered design, key algorithms, WASM memory model, build system, benchmarking pipeline, and security architecture.

---

## Table of Contents

1. [Layered Design](#layered-design)
2. [C Implementation (`src/wasm/`)](#c-implementation-srcwasm)
   - [Module Map](#module-map)
   - [Key Algorithms](#key-algorithms)
3. [JavaScript Wrappers (`src/js/`)](#javascript-wrappers-srcjs)
   - [WASM Wrapper](#wasm-wrapper-mlkem768-wrapperjs)
   - [Pure JS Wrapper](#pure-js-wrapper-purejs-wrapperjs)
4. [Hybrid Key Exchange Design](#hybrid-key-exchange-design)
5. [WASM Memory Model](#wasm-memory-model)
6. [Build System](#build-system)
7. [Benchmarking Architecture](#benchmarking-architecture)
8. [Security Architecture](#security-architecture)
9. [Performance Characteristics](#performance-characteristics)
10. [Known Limitations and Future Work](#known-limitations-and-future-work)

---

## Layered Design

StarryCrypt-PQC uses a four-layer architecture that separates application concerns from cryptographic implementation:

```
┌──────────────────────────────────────────────────────────┐
│  Application Layer                                       │
│  (consumer code — benchmark harness, dashboard, etc.)   │
├──────────────────────────────────────────────────────────┤
│  JavaScript API Layer                                    │
│  src/js/mlkem768-wrapper.js   (WASM backend)             │
│  src/js/purejs-wrapper.js     (pure JS backend)          │
│  — Uniform async API, memory management, hybrid KEx —   │
├──────────────────────────────────────────────────────────┤
│  WASM Bridge (Emscripten auto-generated)                 │
│  — Type marshalling, JS↔WASM heap transfers —            │
│  — Exported runtime methods: ccall, writeArrayToMemory — │
├──────────────────────────────────────────────────────────┤
│  C Cryptographic Core (WASM-compiled)                    │
│  — ML-KEM-768 (FIPS 203), SHA-3/SHAKE (FIPS 202) —      │
│  — Polynomial arithmetic, NTT, Barrett reduction —       │
└──────────────────────────────────────────────────────────┘
```

Both JavaScript wrappers expose an **identical async API** (see [`API.md`](API.md)). The pure JS wrapper replaces the C core with `@noble/post-quantum` (v0.6.1), an independently audited JavaScript ML-KEM implementation. Switching between backends requires only changing the import path.

---

## C Implementation (`src/wasm/`)

The C implementation is derived from [PQClean](https://github.com/PQClean/PQClean) (Apache 2.0), a collection of clean, portable, and formally verified post-quantum cryptographic implementations. It targets the FIPS 203 final standard (ML-KEM-768, K=3).

### Module Map

| File | Responsibility |
|---|---|
| `params.h` | Parameter set: K=3, n=256, q=3329, η₁=2, η₂=2. All size constants derived here. |
| `api.h` | Public C API declarations (`PQCLEAN_MLKEM768_CLEAN_*` naming per PQClean convention). |
| `kem.c` | Top-level KEM: `keypair`, `keypair_derand`, `enc`, `enc_derand`, `dec`. Implements the Fujisaki-Okamoto (FO) CCA transform over the IND-CPA scheme. |
| `indcpa.c` | IND-CPA secure PKE: `indcpa_keypair_derand`, `indcpa_enc`, `indcpa_dec`. Implements the Learning With Errors (LWE) over rings (RLWE) scheme. |
| `poly.c` | Polynomial operations: coefficient reduction, compression/decompression, message encoding, noise sampling. |
| `polyvec.c` | Operations over length-K vectors of polynomials: serialization, NTT, inner products, addition. |
| `ntt.c` | Forward and inverse Number Theoretic Transform (NTT) and Montgomery-domain basemul. |
| `fips202.c` | SHA3-256, SHA3-512, SHAKE128, SHAKE256 — the FIPS 202 hash and XOF primitives used throughout ML-KEM. |
| `cbd.c` | Centered Binomial Distribution (CBD) sampling for noise polynomials (η₁=η₂=2). |
| `reduce.c` | Barrett reduction modulo q=3329 and Montgomery reduction. |
| `verify.c` | Constant-time byte comparison (`verify`) and conditional copy (`cmov`, `cmov_int16`). |
| `symmetric-shake.c` | Glue layer mapping the symmetric primitives (G, H, J, PRF, KDF, XOF) used by ML-KEM to FIPS 202 functions. |
| `randombytes.c` | CSPRNG bridge. In the WASM context, `randombytes()` is satisfied by a JavaScript callback (`crypto.getRandomValues`) injected by the Emscripten module initialization. |
| `wasm_export.c` | `EMSCRIPTEN_KEEPALIVE` export wrappers: thin C shims that expose `mlkem_keypair`, `mlkem_enc`, `mlkem_dec`, and the SHA-3/SHAKE functions to the JavaScript layer via `ccall`. Also provides `mlkem_malloc`, `mlkem_free`, and `mlkem_zeroize`. |
| `benchmark_api.c` | Per-operation timing exports for fine-grained benchmarking (used by the benchmark harness). |
| `compat.h` | Portability macros. Defines `PQCLEAN_PREVENT_BRANCH_HACK` to prevent compiler-specific optimizations that would break constant-time invariants in `verify.c`. |

### Key Algorithms

#### Key Generation

```
Input:  d ← CSPRNG(32 bytes)   // Key seed
        z ← CSPRNG(32 bytes)   // Implicit rejection seed

(ρ, σ) := G(d ∥ k)             // G = SHA3-512; k = KYBER_K = 3
A      := GenMatrix(ρ)         // K×K matrix from SHAKE128 XOF
s, e   := SampleNoise(σ)       // CBD(η₁=2) via PRF(σ, nonce)
t      := NTT⁻¹(A · NTT(s)) + e

pk := (Encode(t) ∥ ρ)
sk := (Encode(s) ∥ pk ∥ H(pk) ∥ z)
```

The dimension-parameter concatenation `G(d ∥ k)` (33-byte input) is the key FIPS 203 modification from Kyber Round 3, providing domain separation across ML-KEM parameter sets.

#### Encapsulation

```
Input:  pk, m ← CSPRNG(32 bytes)

(K̄, r) := G(m ∥ H(pk))        // Multitarget countermeasure
c      := Encrypt_IND-CPA(pk, m, r)
ss     := K̄                    // Shared secret = first 32 bytes of G output
```

The hash of the public key `H(pk)` in the G input is a **multitarget countermeasure**: it binds the ciphertext to a specific public key, preventing adversaries from using one encapsulation to attack multiple recipients simultaneously.

#### Decapsulation (Fujisaki-Okamoto Transform)

```
Input:  ct, sk

m'    := Decrypt_IND-CPA(sk, ct)
(K̄', r') := G(m' ∥ H(pk))
ct'   := Encrypt_IND-CPA(pk, m', r')
fail  := verify(ct, ct')        // Constant-time comparison

// Implicit rejection: compute rejection key unconditionally
ss_reject := J(z ∥ ct)         // J = SHAKE256; z from sk

// Constant-time selection (no secret-dependent branch)
ss := cmov(ss_reject, K̄', fail=0)
```

The re-encryption and constant-time comparison implement the FO implicit-rejection mechanism. An invalid ciphertext returns a pseudo-random value derived from the secret `z` and the ciphertext, making decapsulation indistinguishable from the valid case to an outside observer.

---

## JavaScript Wrappers (`src/js/`)

### WASM Wrapper (`mlkem768-wrapper.js`)

Responsibilities:
- **Module loading**: Injects the Emscripten script via a dynamic `<script>` tag (rather than `import()`) to preserve `document.currentScript.src` for correct `.wasm` binary path resolution.
- **Memory management**: Allocates WASM heap buffers via `mlkem_malloc`, writes input data with `writeArrayToMemory`, reads output data by slicing `Module.HEAPU8`, and calls `mlkem_zeroize` + `mlkem_free` in `finally` blocks to ensure cleanup even on error paths.
- **Type marshalling**: Converts between JavaScript `Uint8Array` and WASM integer pointers.
- **Hybrid key exchange**: X25519 key generation and derivation via `SubtleCrypto`; HKDF-SHA-256 combining the ML-KEM and X25519 shared secrets.
- **Hardware metadata collection**: UA Client Hints, UA string regex fallback, WASM feature probes, timer precision measurement, JS-MIPS baseline.
- **Benchmarking**: Single-handshake (`runHandshake`) and N-iteration statistical benchmark (`runBenchmarkN`).
- **Testing**: `selfTest()` for functional correctness; `verifyConstantTimeRejection()` for FO-path screening.

**Module loading detail:** `MLKEMModule()` (the Emscripten factory) may return either the Module directly or a Promise, depending on the build configuration. The wrapper handles both cases and additionally awaits `mod.ready` if present. A guard checks that `HEAPU8` is populated before returning, catching the case where the `.wasm` binary fails to load silently.

### Pure JS Wrapper (`purejs-wrapper.js`)

Uses `@noble/post-quantum` (imported via CDN ESM: `https://esm.sh/@noble/post-quantum@0.6.1/ml-kem`) as the cryptographic backend. All Web Crypto logic (X25519, HKDF, AES-GCM), hardware metadata collection, and benchmark runner are identical to the WASM wrapper — duplicated rather than imported to avoid cross-module dependency issues in the browser benchmark page.

`loadModule()` is a no-op that returns `true` immediately.

---

## Hybrid Key Exchange Design

The hybrid construction combines the post-quantum security of ML-KEM-768 with the classical security of X25519. It is designed so that breaking the combined key requires breaking **both** primitives simultaneously.

```
Alice                                 Bob
─────                                 ───
mlkemKeyGen()  →  (mlkem_pk, mlkem_sk)
x25519KeyGen() →  (x25519_pub_A, x25519_priv_A)

                ←── mlkem_pk, x25519_pub_A ───

                                      mlkemEncaps(mlkem_pk) → (ct, ss_kem)
                                      x25519KeyGen() → (x25519_pub_B, x25519_priv_B)
                                      x25519Derive(x25519_priv_B, x25519_pub_A) → ss_ecdh
                                      deriveSessionKey(ss_kem, ss_ecdh) → key_bob

                ──── ct, x25519_pub_B ────→

mlkemDecaps(ct, mlkem_sk) → ss_kem
x25519Derive(x25519_priv_A, x25519_pub_B) → ss_ecdh
deriveSessionKey(ss_kem, ss_ecdh) → key_alice

assert(key_alice === key_bob)
```

**Concatenation order:** ML-KEM shared secret precedes X25519 shared secret in the HKDF IKM, following draft-ietf-tls-ecdhe-mlkem-04 §4.3. This ensures that a fully broken X25519 (e.g., by a quantum adversary) does not allow key recovery if ML-KEM remains secure.

**Domain separation:** The HKDF `info` parameter (`'Starrycrypt-PQC v1 | X25519MLKEM768 | AES-256-GCM'`) binds the derived key to this specific application context, preventing cross-protocol key reuse per RFC 5869 §3.2.

---

## WASM Memory Model

### Address Space Layout

```
Linear Memory (initial: 64 MB, ALLOW_MEMORY_GROWTH enabled)
┌───────────────────────────────────────────────────────┐  0x00000000
│  Static data                                          │
│  (global variables, string literals, function tables) │
├───────────────────────────────────────────────────────┤
│  Stack (grows upward)                                 │
│  Size: 1 MB                                           │
├───────────────────────────────────────────────────────┤
│  Heap (malloc arena)                                  │
│  Keys:        pk (1184 B), sk (2400 B)                │
│  Ciphertext:  ct (1088 B)                             │
│  Shared sec:  ss (32 B)                               │
│  Temporaries: NTT buffers, polynomial vectors         │
└───────────────────────────────────────────────────────┘  0x04000000 (64 MB)
```

### Buffer Allocation Pattern

Every exported operation follows this pattern to avoid leaking secrets on error paths:

```javascript
const ptr = _malloc(SIZE);
try {
    heapWrite(inputData, ptr, SIZE);
    const ret = Module.ccall('mlkem_operation', ...);
    if (ret !== 0) throw new Error('Operation failed');
    const output = heapRead(ptr, SIZE);
    return output;
} finally {
    _zeroize(ptr, SIZE);  // Always runs, even if an error was thrown
    _free(ptr);
}
```

### JS↔WASM Data Transfer

- **JS → WASM**: `Module.writeArrayToMemory(uint8Array, ptr)` copies bytes from a `Uint8Array` into the WASM linear memory at the given address.
- **WASM → JS**: `new Uint8Array(Module.HEAPU8.buffer, ptr, len).slice()` creates an independent copy of the WASM memory region. The `.slice()` is essential — a view into `HEAPU8` would become invalid if the WASM memory grows (triggers `detachedBuffer`).

---

## Build System

### Emscripten Compilation Flags

The Makefile compiles all C sources into a single WASM module:

```makefile
EMFLAGS = -O3 -s WASM=1 \
  -s "EXPORTED_RUNTIME_METHODS=[ccall,cwrap,writeArrayToMemory,getValue,setValue,HEAPU8]" \
  -s "EXPORTED_FUNCTIONS=[_mlkem_malloc,_mlkem_free,_mlkem_zeroize,_mlkem_keypair,
                           _mlkem_enc,_mlkem_dec,_sha3_256_wasm,_sha3_512_wasm,_shake256_wasm]" \
  -s MODULARIZE=1 -s EXPORT_NAME="MLKEMModule" \
  -s ALLOW_MEMORY_GROWTH=1 -s INITIAL_MEMORY=64MB
```

| Flag | Rationale |
|---|---|
| `-O3` | Full optimization: enables constant-folding, vectorization, inlining. |
| `WASM=1` | Produce `.wasm` binary (not asm.js fallback). |
| `MODULARIZE=1` | Wrap the module in a factory function (`MLKEMModule()`) rather than executing immediately. Required for multi-instance support. |
| `EXPORT_NAME="MLKEMModule"` | Sets `window.MLKEMModule` as the global factory. |
| `ALLOW_MEMORY_GROWTH=1` | Allows the WASM heap to grow beyond 64 MB if needed (e.g., under memory pressure from GC). |
| `INITIAL_MEMORY=64MB` | Pre-allocates 64 MB to avoid growth events during benchmarking. |

### Makefile Targets

| Target | Action |
|---|---|
| `make all` | Compile `src/wasm/*.c` → `dist/mlkem768.js` + `dist/mlkem768.wasm` |
| `make clean` | Remove `dist/mlkem768.{js,wasm}` |
| `make serve` | Start `python3 -m http.server 8080` |
| `make figures` | Run `analysis/generate_figures.py` using `.venv/bin/python3` |
| `make paper` | Run `make figures`, then compile `paper/main.tex` (pdflatex → bibtex → pdflatex × 2) |
| `make paper-clean` | Remove LaTeX auxiliary files |

---

## Benchmarking Architecture

### Data Collection Flow

```
Browser (benchmark/index.html or benchmark/pure-js.html)
    │
    ├─ selfTest()              — functional correctness gate
    ├─ runBenchmarkN(n, warmup) — statistical benchmark
    │   ├─ warmup × runHandshake()   — JIT/WASM warm-up (untimed)
    │   └─ n × runHandshake()        — timed iterations
    │       ├─ mlkemKeyGen()
    │       ├─ x25519KeyGen() × 2
    │       ├─ mlkemEncaps()
    │       ├─ mlkemDecaps()
    │       ├─ x25519Derive() × 2
    │       ├─ deriveSessionKey() × 2
    │       ├─ aesGcmEncrypt()
    │       └─ aesGcmDecrypt()
    └─ Download result as timestamped JSON
```

### Analysis Pipeline

```
performance_data/starrycrypt_telemetry_2026-05-05.csv
    │
    ├─ scripts/verify_data.py          → Aggregate statistics (stdlib only)
    ├─ scripts/explore_data.py         → Per-subgroup breakdowns (pandas)
    ├─ analysis/statistical_tests.py   → Welch's t-test, Cohen's d, 95% CI
    ├─ analysis/revision_analysis_corrected.py  → Corrected subgroup analysis
    └─ analysis/generate_figures.py    → 8 publication-quality figures (PDF + PNG)
```

### Telemetry Session Schema

Each JSON result file from the benchmark harness is a flat object suitable for appending to the telemetry CSV. The benchmark harnesses previously uploaded to a Supabase Edge Function (now deprecated; `src/js/telemetry.js` is kept for reference only). The committed CSV is the canonical dataset.

---

## Security Architecture

### Constant-Time Design

The constant-time invariant is enforced at three levels:

1. **Algorithm level**: No secret-dependent branches in the core ML-KEM operations. The FO decapsulation uses unconditional re-encryption followed by constant-time comparison (`verify`) and conditional copy (`cmov`).

2. **Implementation level**: `compat.h` defines `PQCLEAN_PREVENT_BRANCH_HACK(b)`, which inserts a volatile read of `b` before it is used as a branch condition. This prevents GCC/Clang from converting the constant-time `cmov` pattern back into a conditional branch during optimization.

3. **WASM compilation level**: `-O3` with Emscripten has been tested to preserve the constant-time invariants from PQClean. However, WASM engines are permitted to use any execution strategy for a valid WASM binary, and JIT-compiled WASM may reintroduce variable-time behavior. This is a fundamental limitation of the browser execution environment.

### Memory Protection Model

```
Secret material lifecycle:
    CSPRNG → WASM heap buffer → C operations → heapRead() copy → JS Uint8Array
                                                                        │
                                                                  (caller uses)
                                                                        │
    mlkem_zeroize (volatile) ← _zeroize(ptr) ← finally block    .fill(0) ←┘
    mlkem_free ← _free(ptr) ←┘
```

### All-Zero Shared Secret Check

The `x25519Derive()` function checks whether the resulting shared secret is all-zero bytes and throws an error if so. This guards against:
- Small-order-point attacks (peer sends a point of low order).
- Implementation bugs that produce a degenerate output.

This check is specified in RFC 8446 §4.2.8 (TLS 1.3) and is referenced in draft-ietf-tls-ecdhe-mlkem-04 §4.3.

---

## Performance Characteristics

### Dominant Latency Factors

| Factor | Approximate Contribution | Notes |
|---|---|---|
| WASM instantiation and initialization | 40–60% of total | One-time cost per page load; not included in per-handshake timings |
| JS/WASM boundary crossings | ~0.5 ms per operation | 3 ccall() invocations per handshake |
| JS garbage collection pauses | 5–30% of tail latency | Non-deterministic; manifests as P99 outliers |
| Cryptographic core (ML-KEM) | ~13% of total handshake | KeyGen: 0.16 ms, Encaps: 0.18 ms, Decaps: 0.19 ms |
| Web Crypto operations | ~5% of total handshake | X25519 derive, HKDF, AES-GCM |

### Why SIMD Does Not Improve Performance Here

The committed WASM binary is compiled **without** SIMD128 intrinsics (`-msimd128`). Observed SIMD "correlation" in the dataset reflects broader hardware capability (faster CPUs with SIMD also have better memory bandwidth, faster JS engines, etc.), not WASM SIMD vectorization of the NTT. This is explicitly noted in the paper.

### Not SIMD-Dependent

Despite SIMD capability being detected via `WebAssembly.validate()` probes, the performance difference between "SIMD-capable" and "non-SIMD" browsers in the dataset is primarily explained by:
1. CPU generation and clock speed.
2. JS engine optimization tier (V8 Turbofan vs. SpiderMonkey IonMonkey).
3. Operating system scheduler behavior.

---

## Known Limitations and Future Work

### Current Limitations

1. **No SIMD128 intrinsics**: The NTT and polynomial arithmetic run in scalar WASM. Compiling with `-msimd128` would enable 128-bit vectorized NTT operations and likely yield a further 2–4x speedup.
2. **No Web Workers support**: ML-KEM operations are single-threaded. `SharedArrayBuffer` and Atomics are available in SIMD-capable browsers and could enable parallel keygen + encaps.
3. **No streaming API**: Large-data applications must load the entire WASM module before processing.
4. **Telemetry upload deprecated**: `src/js/telemetry.js` contains placeholder Supabase credentials. The upload feature is disabled; data collection requires running the benchmark locally.

### Planned Improvements

| Feature | Effort | Impact |
|---|---|---|
| SIMD128 NTT (`-msimd128`) | Medium | 2–4x NTT speedup |
| Web Workers parallelism | High | Parallel keygen + server response |
| ML-KEM-512 / ML-KEM-1024 variants | Low (parameter change) | Security level coverage |
| ML-DSA (FIPS 204) signature support | High (new algorithm) | Complete PQC handshake |
| Web Crypto API polyfill integration | Medium | Fallback for non-SubtleCrypto environments |
| Formal TVLA evaluation | External | Production readiness |
