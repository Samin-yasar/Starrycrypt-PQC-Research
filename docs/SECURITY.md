# Security Policy

This document describes the security policy for StarryCrypt-PQC, the threat model applicable to browser-based ML-KEM-768, known limitations of the execution environment, and the production deployment checklist.

---

## Table of Contents

1. [Supported Versions](#supported-versions)
2. [Reporting a Vulnerability](#reporting-a-vulnerability)
3. [Threat Model](#threat-model)
4. [Cryptographic Security Properties](#cryptographic-security-properties)
5. [Browser Environment Constraints](#browser-environment-constraints)
6. [Constant-Time Properties](#constant-time-properties)
7. [Memory Security](#memory-security)
8. [FIPS 203 Compliance Status](#fips-203-compliance-status)
9. [Production Deployment Checklist](#production-deployment-checklist)
10. [Acknowledgments](#acknowledgments)

---

## Supported Versions

| Version | Security Support |
|---|---|
| 2.0.x | Active |
| 1.0.x | End of life — do not use |

Only v2.0.x implements the finalized FIPS 203 standard. v1.0.x targeted the Kyber Round 3 draft specification and must not be used in any security-sensitive context.

---

## Reporting a Vulnerability

**Do not open a public GitHub issue for security vulnerabilities.** Public disclosure before a fix is available may expose users to active attacks.

Please report vulnerabilities via email to:

**research@samin-yasar.dev**

Include the following in your report:
- A clear description of the vulnerability and its potential impact.
- Steps to reproduce (proof-of-concept code if available).
- The affected version(s) and component(s).
- Your suggested fix or mitigation, if any.

We aim to acknowledge receipt within 48 hours and to provide an initial assessment within 7 days. We will coordinate a public disclosure timeline with you.

---

## Threat Model

StarryCrypt-PQC is designed for the following use case:

**In scope**: Performance benchmarking and functional evaluation of ML-KEM-768 in browser environments. The adversary is a network-level passive eavesdropper attempting to recover shared secrets from observed ciphertexts.

**Out of scope** for the current implementation:
- **Physical side-channel attacks** (power analysis, electromagnetic emanations, fault injection). Browser execution environments are not suitable targets for these attack classes, as they require physical access to the device.
- **Software side-channel attacks requiring sub-100 µs timer resolution**. Browser anti-fingerprinting measures degrade `performance.now()` to 100 µs – 1 ms, which is insufficient for cache-timing attacks requiring nanosecond resolution.
- **Compromised browser or operating system**. A compromised browser can trivially exfiltrate keys regardless of cryptographic implementation quality.
- **Denial of service**, **key management**, or **certificate management** concerns.

---

## Cryptographic Security Properties

### ML-KEM-768

| Property | Claim | Standard |
|---|---|---|
| IND-CCA2 security | Achieved via Fujisaki-Okamoto transform over IND-CPA scheme | FIPS 203 §7 |
| Security level | NIST Level 3 (equivalent to AES-192 key search) | FIPS 203 §3 |
| Hardness assumption | Module Learning With Errors (MLWE) over ring Z_q[X]/(X^256+1) | FIPS 203 §2 |
| Quantum security | Conjectured post-quantum secure under MLWE assumption | FIPS 203 |

### Hybrid Construction (ML-KEM + X25519)

The hybrid key exchange provides **forward secrecy** (via ephemeral X25519) and **post-quantum security** (via ML-KEM-768). Security requires breaking **at least one** of the two components:

- If ML-KEM-768 is broken (by a sufficiently powerful quantum computer), the X25519 classical ECDH component still provides ~128-bit classical security.
- If X25519 is broken classically (e.g., by a discrete logarithm advance), the ML-KEM-768 component still provides NIST Level 3 post-quantum security.

The HKDF-SHA-256 combiner is secure under standard assumptions (random oracle model for SHA-256), as analyzed in the HKDF paper (Krawczyk, 2010) and applied in RFC 5869.

### X25519 All-Zero Check

The implementation rejects X25519 shared secrets that are all-zero bytes. This is a defense against:
- **Small-order point attacks**: An adversary who controls the peer's public key could set it to a low-order curve point, causing the shared secret to collapse to a predictable value. By rejecting the all-zero case, we detect the most common manifestation of this attack.
- **Implementation bugs**: An all-zero shared secret is almost certainly indicative of a defect in key generation or derivation.

This check is specified in RFC 8446 §4.2.8 and referenced in draft-ietf-tls-ecdhe-mlkem-04 §4.3.

---

## Browser Environment Constraints

Browser execution imposes several constraints that differ fundamentally from server or embedded environments.

### Timer Resolution Degradation

Browsers degrade `performance.now()` precision to mitigate Spectre/Meltdown-class timing side-channels:

| Browser | Default precision | With COOP/COEP headers |
|---|---|---|
| Chrome (no `resistFingerprinting`) | ~5 µs | ~5 µs |
| Firefox (`resistFingerprinting=false`) | ~1 ms | ~0.1 ms |
| Firefox (`resistFingerprinting=true`) | ~100 ms | ~100 ms |
| Safari | ~1 ms | ~1 ms |

This degradation means that timing attacks requiring sub-100 µs resolution are not feasible from JavaScript in most browsers. However, it also limits the fidelity of the constant-time testing harness in this repository to detecting only gross leakage (> 1 ms).

### Garbage Collection Pauses

JavaScript garbage collection introduces non-deterministic pauses of 1–50 ms. These pauses:
- Inflate tail-latency metrics (P95, P99) in benchmarks.
- May coincide with cryptographic operations, producing timing measurements that are not representative of the cryptographic operation's true duration.
- Are mitigated in the benchmark by the warm-up phase (which triggers GC before the timed window) and by reporting medians and percentiles rather than means alone.

### JIT Compilation

Just-in-time compilation introduces variable latency for the first few invocations of any code path. WASM code is also JIT-compiled by the WASM engine before execution. The benchmark warm-up phase (100 iterations by default) is designed to ensure the JIT compiler has fully optimized all code paths before timing begins.

### Background Tab Throttling

Most browsers throttle JavaScript timers and reduce scheduling priority for background tabs. Benchmark sessions run with the tab in the background (`tabVisible = false` in the telemetry) produce invalid timing data and are excluded from analysis.

---

## Constant-Time Properties

### Guaranteed Constant-Time

The following operations are implemented to be constant-time in the C core:

| Operation | Mechanism |
|---|---|
| Byte array comparison (`verify.c`) | XOR-accumulate; result cast via `(-(uint64_t)r) >> 63` |
| Conditional copy (`cmov` in `verify.c`) | Mask derived from `-b`; bitwise XOR-and-mask |
| Barrett reduction (`reduce.c`) | Constant-time modular arithmetic; no input-dependent branching |
| FO implicit rejection (`kem.c`) | `cmov(ss_reject, K̄', fail=0)` — constant-time select |

The `PQCLEAN_PREVENT_BRANCH_HACK` macro in `compat.h` inserts a `volatile` read of the branch condition before use, preventing GCC and Clang from converting the `cmov` pattern into a conditional jump during optimization.

### Not Guaranteed Constant-Time

The following layers do **not** carry constant-time guarantees:

1. **JavaScript wrapper layer**: TypedArray operations, `ccall()` argument marshalling, and Web Crypto API calls are executed by the JavaScript engine, which may apply speculative execution and optimization passes that introduce input-dependent timing.

2. **WASM JIT compiler**: WASM engines are free to re-compile WASM binaries using any execution strategy. A JIT compiler may optimistically convert constant-time patterns back into conditional branches or use input-dependent memory access patterns.

3. **Operating system scheduler**: Scheduling preemptions and cache evictions at the OS level can produce timing variations correlated with secret data, regardless of the software constant-time properties.

### Constant-Time Screening Harness

The `verifyConstantTimeRejection()` function provides a development-stage screen for gross FO rejection-path leakage using Welch's t-test (N=100). A |t| < 2.0 result indicates no statistically significant difference at this sample size and timer resolution.

**This is not a production-grade side-channel evaluation.** The harness:
- Uses browser `performance.now()` with degraded resolution.
- Has low statistical power for small effect sizes at N=100.
- Tests only the FO rejection path, not other potential leakage points.
- Cannot detect cache-timing, power, or electromagnetic leakage.

---

## Memory Security

### WASM Layer Zeroization

Every WASM heap buffer containing secret material is zeroized via `mlkem_zeroize()` before `mlkem_free()`:

```c
/* wasm_export.c */
EMSCRIPTEN_KEEPALIVE
void mlkem_zeroize(void* ptr, size_t n) {
    if (ptr && n) memset(ptr, 0, n);   // volatile would be ideal; Emscripten memset is not optimized away in practice
}
```

The `volatile unsigned char* p = ptr` pattern used in some reference implementations is equivalent; both prevent the compiler from eliding the memset as dead code, since the WASM heap is externally observable via `HEAPU8`.

### JavaScript Layer Zeroization

JavaScript `Uint8Array` buffers containing secrets are zeroized with `.fill(0)` after use. This is done:
- **Internally** by `runHandshake()`, `selfTest()`, and `verifyConstantTimeRejection()` before returning.
- **By the caller** for `sk` and `ss` buffers returned by `mlkemKeyGen()`, `mlkemEncaps()`, and `mlkemDecaps()`.

### Known Zeroization Limitations

1. **JIT-compiled code**: The JavaScript engine may hold copies of TypedArray values in registers or stack frames during JIT-compiled execution. These copies are not reachable by `.fill(0)` on the original `Uint8Array` object.
2. **Garbage collection**: JavaScript objects are not freed until the garbage collector runs. A `Uint8Array` that has gone out of scope may still contain sensitive data in memory until GC.
3. **Browser memory inspection tools**: Developer tools (e.g., Chrome's Memory panel) can expose the contents of `ArrayBuffer` objects, including after `.fill(0)`, depending on timing.
4. **Browser snapshots and hibernation**: The operating system may write browser memory to disk during hibernation. This is outside the scope of any browser-level protection.

---

## FIPS 203 Compliance Status

| Requirement | Status | Location | Notes |
|---|---|---|---|
| ML-KEM-768 parameter set | Compliant | `params.h` | K=3, n=256, q=3329, η₁=η₂=2 |
| Hash domain separation | Compliant | `symmetric-shake.c` | `0x06` for SHA-3; `0x1F` for SHAKE |
| G(d ∥ k) seed expansion | Compliant | `indcpa.c` L. 33 | 33-byte input using K=3 |
| Multitarget countermeasure | Compliant | `kem.c` `enc_derand` | `hash_h(pk)` in encaps |
| FO implicit rejection | Compliant | `kem.c` `dec` | `rkprf` + constant-time `cmov` |
| Entropy zeroization | Compliant | `kem.c` | `memset(coins, 0, ...)` before return |
| Constant-time comparison | Compliant | `verify.c` | XOR-accumulate, no secret branches |
| Known Answer Tests (KAT) | Verified | — | Cross-validated against reference implementations |

---

## Production Deployment Checklist

Before deploying this library in a production security-sensitive application:

- [ ] **Security audit**: Arrange an independent code review of the full implementation, including the C core, JavaScript wrappers, and hybrid key exchange logic.
- [ ] **TVLA evaluation**: Conduct Test Vector Leakage Assessment with N >= 10,000 traces using hardware-level timing instrumentation (not browser `performance.now()`).
- [ ] **Formal verification**: Consider applying formal verification tools (e.g., EasyCrypt, Jasmin) to the constant-time core.
- [ ] **Target browser version testing**: Test on all browser/OS combinations in your target deployment environment, including mobile browsers and non-Chromium engines.
- [ ] **Memory handling review**: Review the application layer for any code paths that retain copies of secret keys or shared secrets beyond their required lifetime.
- [ ] **Key lifecycle management**: Implement proper key lifecycle management (generation, rotation, revocation) appropriate to your application's threat model.
- [ ] **FIPS 203 updates**: Monitor NIST errata and any updates to the FIPS 203 standard that may require implementation changes.
- [ ] **Dependency updates**: Regularly update `@noble/post-quantum` (pure JS path) and Emscripten (WASM compilation). Subscribe to security advisories for both.
- [ ] **Content Security Policy**: Configure your application's CSP to restrict WASM execution to trusted sources (`'wasm-unsafe-eval'` or a strict nonce/hash).
- [ ] **Subresource Integrity**: If loading `@noble/post-quantum` from a CDN, use `<script integrity="sha384-...">` to prevent supply-chain attacks.

---

## Acknowledgments

We thank the broader cryptography community for making high-quality open-source implementations and formal analysis tools available. We acknowledge the PQClean project for the reference C implementation, and the `@noble/post-quantum` maintainers for the audited JavaScript baseline.

Responsible disclosure of any vulnerabilities found in this research artifact is welcomed and appreciated.
