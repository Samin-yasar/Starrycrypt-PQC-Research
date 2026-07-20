# API Reference

This document is the complete JavaScript API reference for StarryCrypt-PQC v2.0.1.

Both implementations — WASM (`src/js/mlkem768-wrapper.js`) and pure JavaScript (`src/js/purejs-wrapper.js`) — export an **identical async API**. Switching backends requires only changing the import path. All functions are asynchronous and return Promises.

---

## Table of Contents

1. [Constants](#constants)
2. [Module Lifecycle](#module-lifecycle)
3. [Core ML-KEM-768 Operations](#core-ml-kem-768-operations)
   - [mlkemKeyGen](#mlkemkeygen)
   - [mlkemEncaps](#mlkemencaps)
   - [mlkemDecaps](#mlkemdecaps)
4. [X25519 Key Exchange](#x25519-key-exchange)
   - [checkX25519Support](#checkx25519support)
   - [x25519KeyGen](#x25519keygen)
   - [x25519Derive](#x25519derive)
5. [Key Derivation and Encryption](#key-derivation-and-encryption)
   - [hkdfSha256](#hkdfsha256)
   - [deriveSessionKey](#derivesessionkey)
   - [aesGcmEncrypt](#aesgcmencrypt)
   - [aesGcmDecrypt](#aesgcmdecrypt)
6. [Benchmarking](#benchmarking)
   - [runHandshake](#runhandshake)
   - [runBenchmarkN](#runbenchmarkn)
7. [Testing and Verification](#testing-and-verification)
   - [selfTest](#selftest)
   - [verifyConstantTimeRejection](#verifyconstanttimerejection)
8. [Hardware Metadata](#hardware-metadata)
   - [getHardwareMeta](#gethardwaremeta)
9. [Error Handling](#error-handling)
10. [Memory Safety Contract](#memory-safety-contract)

---

## Constants

These constants reflect the FIPS 203 ML-KEM-768 parameter set and are exported from both wrapper modules.

```javascript
const MLKEM_PUBLICKEYBYTES  = 1184;  // Public key size (bytes)
const MLKEM_SECRETKEYBYTES  = 2400;  // Secret key size (bytes)
const MLKEM_CIPHERTEXTBYTES = 1088;  // Ciphertext size (bytes)
const MLKEM_SSBYTES         = 32;    // Shared secret size (bytes)
```

These sizes are derived from the ML-KEM-768 parameter set (K=3, n=256, q=3329):

| Parameter | Value | Formula |
|---|---|---|
| Public key | 1184 bytes | K × 384 + 32 |
| Secret key | 2400 bytes | K × 384 + 1184 + 2 × 32 |
| Ciphertext | 1088 bytes | K × 320 + 128 |
| Shared secret | 32 bytes | Fixed |

---

## Module Lifecycle

### `loadModule(wasmUrl?)`

*WASM wrapper only.* Loads and initializes the Emscripten WASM module. Must be called once before any ML-KEM operations. Subsequent calls return the cached module immediately.

```typescript
async function loadModule(wasmUrl?: string): Promise<EmscriptenModule>
```

**Parameters:**

| Parameter | Type | Default | Description |
|---|---|---|---|
| `wasmUrl` | `string` | `'./dist/mlkem768.js'` | URL of the Emscripten JS loader file. The `.wasm` binary is resolved relative to this URL by Emscripten. |

**Returns:** The initialized Emscripten module object.

**Throws:**
- If the script at `wasmUrl` cannot be loaded (network error, 404).
- If `window.MLKEMModule` is not defined after script execution (wrong file or corrupt build).
- If the WASM heap fails to initialize (`.wasm` binary not found or corrupt).

**Implementation note:** The WASM module is loaded via a dynamically injected `<script>` tag rather than `import()`. This is required because the Emscripten classic (non-module) build uses `document.currentScript.src` to resolve the `.wasm` binary path, which is `null` inside ES modules.

```javascript
import { loadModule } from './src/js/mlkem768-wrapper.js';

// Load once at application startup
await loadModule('./dist/mlkem768.js');

// Subsequent calls are no-ops that return the cached module
await loadModule(); // OK
```

For the **pure JS** wrapper, `loadModule()` is a no-op that returns `true` immediately, since `@noble/post-quantum` is a standard ES module import.

---

## Core ML-KEM-768 Operations

### `mlkemKeyGen()`

Generates an ML-KEM-768 keypair. Randomness is sourced from `crypto.getRandomValues()` via the WASM `randombytes` callback.

```typescript
async function mlkemKeyGen(): Promise<{
    pk: Uint8Array,   // Public key  (1184 bytes)
    sk: Uint8Array,   // Secret key  (2400 bytes)
    timeMs: number    // Wall-clock time for the C-level operation (ms)
}>
```

**Side effects (WASM only):** Allocates and then frees two WASM heap buffers. The `sk` buffer is zeroized with `mlkem_zeroize()` before `mlkem_free()`.

**Security note:** The caller is responsible for zeroizing the returned `sk` after use: `sk.fill(0)`.

```javascript
const { pk, sk, timeMs } = await mlkemKeyGen();
console.log(`KeyGen: ${timeMs.toFixed(3)} ms`);
console.log(`pk: ${pk.length} bytes, sk: ${sk.length} bytes`);

// ... use pk and sk ...

// Zeroize when done
sk.fill(0);
```

---

### `mlkemEncaps(pk)`

Encapsulates to a public key, producing a ciphertext and shared secret. This is the operation performed by the **initiator** (e.g., a TLS client).

```typescript
async function mlkemEncaps(pk: Uint8Array): Promise<{
    ct: Uint8Array,   // Ciphertext    (1088 bytes)
    ss: Uint8Array,   // Shared secret (32 bytes)
    timeMs: number    // Wall-clock time for the C-level operation (ms)
}>
```

**Parameters:**

| Parameter | Type | Constraint |
|---|---|---|
| `pk` | `Uint8Array` | Must be exactly 1184 bytes. Throws `Error` otherwise. |

**Side effects (WASM only):** Zeroizes `ss` and `pk` WASM heap buffers before freeing them.

**Security note:** The returned `ss` is sensitive. Zeroize after use: `ss.fill(0)`.

```javascript
const { ct, ss, timeMs } = await mlkemEncaps(pk);
// Send ct to the decapsulator; ss is the shared secret on this side
ss.fill(0); // Zeroize after deriving session key
```

---

### `mlkemDecaps(ct, sk)`

Decapsulates a ciphertext using a secret key, recovering the shared secret. This is the operation performed by the **responder** (e.g., a TLS server).

If `ct` is invalid or has been tampered with, `mlkemDecaps` returns a **pseudo-random** value (the implicit rejection output of the Fujisaki-Okamoto transform) rather than throwing an error. This is the correct FIPS 203 behavior and prevents ciphertext-validity oracle attacks.

```typescript
async function mlkemDecaps(ct: Uint8Array, sk: Uint8Array): Promise<{
    ss: Uint8Array,   // Shared secret or pseudo-random rejection value (32 bytes)
    timeMs: number    // Wall-clock time for the C-level operation (ms)
}>
```

**Parameters:**

| Parameter | Type | Constraint |
|---|---|---|
| `ct` | `Uint8Array` | Must be exactly 1088 bytes. Throws `Error` otherwise. |
| `sk` | `Uint8Array` | Must be exactly 2400 bytes. Throws `Error` otherwise. |

**Side effects (WASM only):** Zeroizes `ss` and `sk` WASM heap buffers before freeing them.

**Security note:** The returned `ss` is sensitive. Zeroize after use: `ss.fill(0)`.

```javascript
const { ss, timeMs } = await mlkemDecaps(ct, sk);
// ss === the encapsulator's ss if ct was valid
sk.fill(0);  // Zeroize secret key
ss.fill(0);  // Zeroize shared secret after deriving session key
```

---

## X25519 Key Exchange

These functions wrap the browser's Web Crypto API (`SubtleCrypto`). They are identical in both the WASM and pure JS wrappers.

### `checkX25519Support()`

Probes whether the current browser's Web Crypto implementation supports X25519 key exchange. Result is cached after the first call.

```typescript
async function checkX25519Support(): Promise<boolean>
```

```javascript
const hasX25519 = await checkX25519Support();
if (!hasX25519) {
    console.warn('X25519 not available; falling back to ML-KEM-only key exchange');
}
```

---

### `x25519KeyGen()`

Generates an X25519 ephemeral keypair via `SubtleCrypto.generateKey()`. The private scalar is held as an opaque `CryptoKey` handle — it is **never exported to the JavaScript heap**.

```typescript
async function x25519KeyGen(): Promise<{
    publicKey: Uint8Array,    // 32-byte raw public key
    privateKey: CryptoKey     // Opaque Web Crypto handle; not accessible from JS
}>
```

```javascript
const { publicKey, privateKey } = await x25519KeyGen();
// publicKey: Uint8Array (32 bytes) — safe to transmit
// privateKey: CryptoKey — never touches JS memory
```

---

### `x25519Derive(privateKey, peerPublicKey)`

Computes the X25519 shared secret from a local private key and a peer's public key via `SubtleCrypto.deriveBits()`.

```typescript
async function x25519Derive(
    privateKey: CryptoKey,
    peerPublicKey: Uint8Array
): Promise<Uint8Array>  // 32-byte shared secret
```

**Parameters:**

| Parameter | Type | Description |
|---|---|---|
| `privateKey` | `CryptoKey` | The `privateKey` handle returned by `x25519KeyGen()`. |
| `peerPublicKey` | `Uint8Array` | The peer's 32-byte raw X25519 public key. |

**Throws:** `Error` if the resulting shared secret is all-zero bytes, which indicates a small-order point or invalid public key. This check follows RFC 8446 §4.2.8 and draft-ietf-tls-ecdhe-mlkem-04 §4.3.

```javascript
const aliceX = await x25519KeyGen();
const bobX   = await x25519KeyGen();

const ssAlice = await x25519Derive(aliceX.privateKey, bobX.publicKey);
const ssBob   = await x25519Derive(bobX.privateKey,   aliceX.publicKey);
// ssAlice byte-equals ssBob
```

---

## Key Derivation and Encryption

### `hkdfSha256(ikm, salt, info, outLen?)`

HKDF-SHA-256 key derivation via `SubtleCrypto.deriveBits()` (RFC 5869).

```typescript
async function hkdfSha256(
    ikm: Uint8Array,       // Input keying material
    salt: Uint8Array,      // Salt (use empty Uint8Array for no salt)
    info: Uint8Array,      // Application-specific context/domain separation
    outLen?: number        // Output length in bytes (default: 32)
): Promise<Uint8Array>
```

```javascript
const key = await hkdfSha256(
    ikm,
    new Uint8Array(0),                                    // empty salt
    new TextEncoder().encode('MyApp v1 | context'),       // domain separation
    32
);
```

---

### `deriveSessionKey(mlkemSS, x25519SS, context?)`

Derives a 32-byte AES-256-GCM session key by combining the ML-KEM-768 and X25519 shared secrets via HKDF-SHA-256. Concatenation order follows draft-ietf-tls-ecdhe-mlkem-04 §4.3 (ML-KEM first).

```typescript
async function deriveSessionKey(
    mlkemSS:  Uint8Array,    // ML-KEM-768 shared secret (32 bytes)
    x25519SS: Uint8Array,    // X25519 shared secret     (32 bytes)
    context?: Uint8Array     // HKDF info field (domain separation)
): Promise<Uint8Array>       // 32-byte session key
```

**Default `context`:** `new TextEncoder().encode('Starrycrypt-PQC v1 | X25519MLKEM768 | AES-256-GCM')`

**Throws:** `Error` if either input is not exactly 32 bytes.

**Side effects:** The 64-byte concatenated IKM buffer is zeroized after HKDF completes.

```javascript
const sessionKey = await deriveSessionKey(mlkemSS, x25519SS);
mlkemSS.fill(0);
x25519SS.fill(0);
// Use sessionKey for AES-256-GCM ...
sessionKey.fill(0); // Zeroize when done
```

---

### `aesGcmEncrypt(key, plaintext, iv)`

AES-256-GCM authenticated encryption via `SubtleCrypto.encrypt()`.

```typescript
async function aesGcmEncrypt(
    key:       Uint8Array,   // 32-byte AES-256-GCM key
    plaintext: Uint8Array,   // Plaintext of arbitrary length
    iv:        Uint8Array    // 12-byte initialization vector (must be unique per key)
): Promise<Uint8Array>       // Ciphertext + 16-byte GCM authentication tag
```

**Security requirement:** The IV must be unique for every encryption under the same key. Use `crypto.getRandomValues(new Uint8Array(12))` to generate IVs.

---

### `aesGcmDecrypt(key, ciphertext, iv)`

AES-256-GCM authenticated decryption via `SubtleCrypto.decrypt()`.

```typescript
async function aesGcmDecrypt(
    key:        Uint8Array,   // 32-byte AES-256-GCM key
    ciphertext: Uint8Array,   // Ciphertext including the 16-byte GCM tag
    iv:         Uint8Array    // 12-byte IV used during encryption
): Promise<Uint8Array>        // Plaintext
```

**Throws:** `DOMException` (name: `"OperationError"`) if GCM tag verification fails, indicating ciphertext tampering or key mismatch. Do not use the output if this throws.

---

## Benchmarking

### `runHandshake()`

Executes a single complete handshake round-trip: ML-KEM keygen → encaps → decaps → X25519 exchange → HKDF → AES-GCM encrypt → AES-GCM decrypt. Verifies that both sides derive identical session keys.

```typescript
async function runHandshake(): Promise<{
    keysMatch: boolean,      // true if Alice and Bob derived the same session key
    timing: {
        mlkemKeyGenMs:    number,
        mlkemEncapsMs:    number,
        mlkemDecapsMs:    number,
        x25519ExchangeMs: number,
        hkdfMs:           number,
        aesGcmEncryptMs:  number,
        aesGcmDecryptMs:  number,
        totalHandshakeMs: number    // End-to-end wall clock time
    },
    sizes: {
        mlkemPublicKeyBytes:    number,   // 1184
        mlkemSecretKeyBytes:    number,   // 2400
        mlkemCiphertextBytes:   number,   // 1088
        mlkemSharedSecretBytes: number,   // 32
        sessionKeyBytes:        number,   // 32
        aesCiphertextBytes:     number    // plaintext + 16 (GCM tag)
    }
}>
```

All secrets are zeroized before the function returns.

---

### `runBenchmarkN(n?, warmup?)`

Runs `n` timed handshake iterations preceded by `warmup` untimed warm-up iterations. Returns IEEE-style descriptive statistics for each timing field.

```typescript
async function runBenchmarkN(
    n?:      number,    // Timed iterations  (default: 50; minimum: 1)
    warmup?: number     // Warm-up iterations (default: 100)
): Promise<BenchmarkReport>
```

The warm-up phase forces JIT compilation and WASM module optimization before the timed window begins, preventing first-run overhead from skewing results. The warm-up default of 100 iterations is intentionally high to ensure stable V8/SpiderMonkey optimization tiers are reached.

**Return type — `BenchmarkReport`:**

```typescript
interface TimingStats {
    mean:   number,   // Arithmetic mean (ms)
    stdDev: number,   // Population standard deviation (ms)
    median: number,   // 50th percentile (ms)
    p5:     number,   // 5th percentile  (ms)
    p95:    number,   // 95th percentile (ms)
    p99:    number,   // 99th percentile (ms)
    min:    number,   // Minimum observed (ms)
    max:    number    // Maximum observed (ms)
}

interface BenchmarkReport {
    hardware:   HardwareMeta,   // Browser and device metadata (see getHardwareMeta)
    runs:       number,         // n (timed iterations)
    warmupRuns: number,         // warmup iterations
    keysMatch:  boolean,        // true if all runs verified key agreement
    timing: {
        mlkemKeyGenMs:    TimingStats,
        mlkemEncapsMs:    TimingStats,
        mlkemDecapsMs:    TimingStats,
        x25519ExchangeMs: TimingStats,
        hkdfMs:           TimingStats,
        aesGcmEncryptMs:  TimingStats,
        aesGcmDecryptMs:  TimingStats,
        totalHandshakeMs: TimingStats
    },
    sizes: { ... }   // same as runHandshake
}
```

```javascript
const report = await runBenchmarkN(50, 10);

console.log(`Mean total handshake: ${report.timing.totalHandshakeMs.mean} ms`);
console.log(`P95 total handshake:  ${report.timing.totalHandshakeMs.p95} ms`);
console.log(`All keys matched:     ${report.keysMatch}`);

// Download as JSON (as done in the benchmark harness)
const blob = new Blob([JSON.stringify(report, null, 2)], { type: 'application/json' });
const a = document.createElement('a');
a.href = URL.createObjectURL(blob);
a.download = `starrycrypt_${Date.now()}.json`;
a.click();
```

---

## Testing and Verification

### `selfTest()`

Performs a full keygen → encaps → decaps round-trip and verifies:
1. All output byte lengths match FIPS 203 ML-KEM-768 exactly.
2. Encapsulator and decapsulator derive identical shared secrets.
3. Hybrid X25519 + ML-KEM key agreement produces matching session keys.

```typescript
async function selfTest(): Promise<{
    passed: boolean,
    checks: Array<{
        name:     string,
        actual:   number | boolean,
        expected: number | boolean
    }>
}>
```

Call `selfTest()` before running benchmarks to confirm the implementation is producing correct output. All secrets are zeroized before the function returns.

```javascript
const { passed, checks } = await selfTest();

if (!passed) {
    const failed = checks.filter(c => c.actual !== c.expected);
    console.error('Self-test failures:', failed);
    throw new Error('ML-KEM self-test failed — do not proceed with benchmarking');
}
console.log('Self-test passed:', checks.length, 'checks');
```

---

### `verifyConstantTimeRejection(n?)`

*WASM wrapper only.* Heuristic screening test for timing leakage in the Fujisaki-Okamoto implicit-rejection path.

Runs `n` interleaved decapsulations of a valid ciphertext and a 1-bit-corrupted ciphertext, then computes Welch's t-test on the two timing distributions. A |t| < 2.0 (α = 0.05, two-tailed) indicates no statistically significant timing difference at this sample size.

```typescript
async function verifyConstantTimeRejection(
    n?: number   // Iterations per path (default: 100)
): Promise<{
    validPath:   { mean: number, stdDev: number, n: number },
    invalidPath: { mean: number, stdDev: number, n: number },
    tStatistic:  number,
    constantTime: boolean,      // true when |tStatistic| < 2.0
    interpretation: string      // Human-readable result summary
}>
```

**Limitations:**
- Browser timer resolution is degraded to 100 µs – 1 ms by anti-fingerprinting measures. Only gross leakage (>> 1 ms difference) is detectable.
- N=100 has low statistical power for small effect sizes. Production evaluation requires N >= 10,000 with hardware-level timing.
- Does not test other potential leakage vectors (cache side-channels, power analysis).

```javascript
const result = await verifyConstantTimeRejection(100);

console.log(`t-statistic: ${result.tStatistic}`);
console.log(`Constant-time screen: ${result.constantTime ? 'PASS' : 'FAIL'}`);
console.log(result.interpretation);
```

---

## Hardware Metadata

### `getHardwareMeta()`

Collects structured, non-identifiable device and browser metadata for reproducible benchmark reporting. Used internally by `runBenchmarkN()`.

```typescript
async function getHardwareMeta(): Promise<HardwareMeta>

interface HardwareMeta {
    ramGiB:          number | null,    // navigator.deviceMemory (rounded to nearest GiB)
    logicalCores:    number | null,    // navigator.hardwareConcurrency
    platform:        string,           // OS platform string
    osName:          string,           // e.g., "macOS", "Android", "Windows"
    osVersion:       string,           // OS version string
    browserName:     string,           // e.g., "Chrome", "Safari", "Firefox"
    browserVersion:  string,           // Browser version string
    deviceType:      string,           // "mobile" | "desktop" | "tablet" | "unknown"
    deviceModel:     string | null,    // Device model (Chromium UA Client Hints only)
    userAgent:       string,           // Raw UA string (retained for audit; not used as ID)
    wasmFeatures: {
        simd:        boolean,          // WASM SIMD128 (v128.const opcode probe)
        threads:     boolean,          // WASM Threads (SharedArrayBuffer + shared memory)
        bulkMemory:  boolean,          // WASM Bulk Memory (memory.copy opcode probe)
        relaxedSimd: boolean           // Relaxed SIMD (i32x4.relaxed_trunc probe)
    },
    timerPrecisionMs: number | null,   // Effective performance.now() tick granularity (ms)
    tabVisible:       boolean,         // false if tab is in background (throttled timers)
    baselineMips:     number | null    // JS xorshift throughput (millions of ops/second)
}
```

**Detection strategy:**
1. UA Client Hints API (Chromium >= 89) — highest accuracy on Android and Windows.
2. UA string regex fallback — covers Firefox, Safari, and older browsers.
3. WASM feature probes — compile minimal hand-crafted WASM binaries to test feature support.
4. Timer precision measurement — 20-transition median delta loop.
5. Baseline MIPS — 1M-iteration deterministic xorshift PRNG loop (~20 ms).

---

## Error Handling

All functions throw `Error` instances with descriptive messages. Recommended pattern:

```javascript
try {
    await loadModule('./dist/mlkem768.js');
    const { pk, sk } = await mlkemKeyGen();
    const { ct, ss } = await mlkemEncaps(pk);
    const { ss: ssDecaps } = await mlkemDecaps(ct, sk);
    // ...
} catch (err) {
    if (err.message.includes('WASM')) {
        console.error('Module load failure:', err.message);
    } else if (err.message.includes('Bad pk length')) {
        console.error('Invalid public key size:', err.message);
    } else {
        console.error('Unexpected error:', err);
    }
}
```

Common error messages:

| Message | Cause |
|---|---|
| `"WASM module not initialized"` | Called a KEM function before `loadModule()` |
| `"Failed to load WASM script: <url>"` | Network error or wrong URL in `loadModule()` |
| `"WASM heap not initialized"` | `.wasm` binary not found (404) or corrupt |
| `"Bad pk length"` | `pk.length !== 1184` passed to `mlkemEncaps` |
| `"Bad ct length"` | `ct.length !== 1088` passed to `mlkemDecaps` |
| `"Bad sk length"` | `sk.length !== 2400` passed to `mlkemDecaps` |
| `"X25519 shared secret is all-zero"` | Small-order-point attack or invalid peer public key |
| `"Bad SS lengths"` | Inputs to `deriveSessionKey` are not both 32 bytes |

---

## Memory Safety Contract

The following contract governs how secret material is handled across the JS/WASM boundary.

### WASM Layer

1. `mlkem_zeroize(ptr, len)` is called on every WASM heap buffer holding a secret key (`sk`) or shared secret (`ss`) **before** `mlkem_free(ptr)`.
2. `mlkem_zeroize` is implemented as a `volatile memset`, preventing compiler dead-code elimination.
3. Public keys and ciphertexts are not zeroized (they are not secret).

### JavaScript Layer

1. The caller is responsible for calling `.fill(0)` on any `Uint8Array` containing secret material after use.
2. X25519 private keys are `CryptoKey` handles; their memory is managed by the browser's Web Crypto implementation and is **not accessible from JavaScript**.
3. The 64-byte intermediate IKM buffer in `deriveSessionKey` is zeroized before the function returns.
4. `runHandshake()`, `selfTest()`, and `verifyConstantTimeRejection()` internally zeroize all secrets before returning.

### Known Limitations

- JIT-compiled JavaScript may hold additional copies of values in registers or stack frames that are not reachable by `.fill(0)`.
- Garbage collection may delay deallocation of JavaScript objects containing sensitive data.
- Browser memory snapshotting tools may expose TypedArray contents even after `.fill(0)`.

These limitations are inherent to the browser execution environment and are documented in [`docs/SECURITY.md`](SECURITY.md).
