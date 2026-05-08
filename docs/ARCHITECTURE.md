# Architecture

## Overview

StarryCrypt-PQC consists of four main layers:

```
┌─────────────────────────────────────────┐
│  Application Layer (Your Code)          │
├─────────────────────────────────────────┤
│  JavaScript Wrappers                    │
│  • mlkem768-wrapper.js (WASM)           │
│  • purejs-wrapper.js (Pure JS)          │
├─────────────────────────────────────────┤
│  WASM Bridge (Auto-generated)           │
│  • Memory management                    │
│  • Type marshalling                     │
├─────────────────────────────────────────┤
│  C Implementation (WASM-compiled)       │
│  • ML-KEM-768 (FIPS 203)                │
│  • SHA-3 / SHAKE (FIPS 202)             │
│  • Polynomial arithmetic                  │
└─────────────────────────────────────────┘
```

## Core Components

### ML-KEM-768 Implementation

Located in `src/wasm/`:

| File | Purpose |
|------|---------|
| `kem.c` | Key encapsulation mechanism (keygen, encaps, decaps) |
| `indcpa.c` | IND-CPA secure public-key encryption |
| `poly.c` | Polynomial arithmetic over R_q |
| `polyvec.c` | Vector of polynomials |
| `ntt.c` | Number Theoretic Transform |
| `fips202.c` | SHA-3 and SHAKE implementations |
| `verify.c` | Constant-time comparison |
| `wasm_export.c` | WASM-specific exports |

### Key Algorithms

#### Key Generation
```
d = random(32)          // Random seed
z = random(32)          // Implicit rejection seed
(pk, sk') = KEM.KeyGen_internal(d)
sk = sk' || pk || H(pk) || z
```

#### Encapsulation
```
m = random(32)          // Random message
K̄, r = G(m || H(pk))
c = KEM.Enc_internal(pk, m, r)
K = KDF(K̄ || H(c), 32)
```

#### Decapsulation
```
m' = KEM.Dec_internal(sk, c)
K̄', r' = G(m' || h)
c' = KEM.Enc_internal(pk, m', r')
if c == c':
    return KDF(K̄' || H(c), 32)
else:
    return KDF(z || H(c), 32)  // Implicit rejection
```

### Hybrid Key Exchange

Combines ML-KEM-768 with X25519:

```
ML-KEM shared secret: ss_kem (32 bytes)
X25519 shared secret: ss_ecdh (32 bytes)
Combined: HKDF-SHA-256(ss_kem || ss_ecdh, "hybrid-kex", 32)
```

## Memory Layout

### WASM Memory Model

```
┌──────────────────────────────────────┐ 0x0000
│ Stack (grows down)                   │
├──────────────────────────────────────┤
│ Heap (grows up)                      │
│   • Keys                             │
│   • Ciphertexts                      │
│   • Temporary buffers                │
├──────────────────────────────────────┤
│ Static data                          │
└──────────────────────────────────────┘ 64MB
```

Initial memory: 64MB
Stack size: 1MB
Growth: Dynamic (ALLOW_MEMORY_GROWTH)

### Buffer Sizes

| Object | Size (bytes) |
|--------|--------------|
| Public Key | 1184 |
| Secret Key | 2400 |
| Ciphertext | 1088 |
| Shared Secret | 32 |

## JavaScript Wrappers

### WASM Wrapper (`mlkem768-wrapper.js`)

Handles:
- Module loading and initialization
- Memory allocation in WASM heap
- Data marshalling (Uint8Array ↔ WASM pointers)
- Secure cleanup
- Hybrid X25519 integration

### Pure JS Wrapper (`purejs-wrapper.js`)

Uses `@noble/post-quantum` for comparison baseline:
- Same API as WASM version
- No WASM compilation required
- Slower but wider browser support

## Benchmarking System

### Data Collection

```
benchmark/
├── index.html          # Main benchmark page
└── pure-js.html        # Pure JS comparison
```

Telemetry includes:
- Per-phase timing (KeyGen, Encaps, Decaps)
- Total handshake latency
- Browser capabilities (SIMD, threads, bulk memory)
- Device info (via user agent analysis)
- Baseline MIPS (JetStream 3 benchmark)

### Analysis Pipeline

```
Telemetry CSV
    ↓
analysis/generate_figures.py
    ↓
Publication-ready PDFs
```

## Build System

### Emscripten Compilation

```
C Sources
    ↓
emcc (Emscripten)
    ↓
dist/mlkem768.js      (JS loader)
dist/mlkem768.wasm    (Binary module)
```

### Exported Functions

From `wasm_export.c`:
- `mlkem_malloc` / `mlkem_free`
- `mlkem_zeroize`
- `mlkem_keypair`
- `mlkem_enc`
- `mlkem_dec`
- `sha3_256_wasm` / `sha3_512_wasm`
- `shake256_wasm`

## Security Architecture

### Constant-Time Design

1. **No secret branches**: All conditional operations use constant-time selects
2. **Barrett reduction**: Prevents timing leaks from modular reduction
3. **Verify functions**: `verify.c` provides constant-time comparison

### Memory Protection

```c
void mlkem_zeroize(void* ptr, size_t len) {
    volatile unsigned char* p = ptr;
    while (len--) *p++ = 0;
}
```

## Performance Characteristics

### Dominant Factors

1. **Browser Runtime**: Modern engines (Chrome 120+, Safari 17+) significantly faster
2. **WASM vs JS**: Compiled binary execution vs interpretation
3. **Memory overhead**: JS/WASM boundary crossing adds ~0.5ms per operation
4. **Garbage Collection**: Non-deterministic, affects tail latency

### Not SIMD-Dependent

Despite SIMD capability being detected:
- WASM binary compiled without SIMD128 intrinsics
- Performance difference reflects broader runtime optimization
- Safari non-SIMD achieves excellent performance (median 0.49ms)

## Future Improvements

### Potential Optimizations

1. **SIMD128**: Compile with `-msimd128` for vectorized NTT
2. **Multi-threading**: Web Workers for parallel operations
3. **Streaming**: Process large data incrementally
4. **Precomputation**: Cache NTT twiddle factors

### Research Directions

- Formal verification of constant-time properties
- TVLA evaluation with hardware timers
- Additional lattice-based primitives (ML-DSA)
