/**
 * @file benchmark_api.c
 * @brief Emscripten KEEPALIVE exports for ML-KEM-768 benchmarking.
 *
 * This file is an alternate WASM export layer used exclusively by the
 * benchmarking harness (scripts/benchmark.js and the browser-based
 * performance test suite). It mirrors the exported symbols from
 * wasm_export.c but omits the extended Doxygen documentation so that the
 * benchmarking WASM binary remains compact.
 *
 * EXPORTED SYMBOLS
 * ----------------
 *   Memory helpers : mlkem_malloc, mlkem_free, mlkem_zeroize
 *   KEM operations : mlkem_keypair, mlkem_enc, mlkem_dec
 *   FIPS 202 hashes: sha3_256_wasm, sha3_512_wasm, shake256_wasm
 *
 * COMPILE-TIME SAFETY
 * -------------------
 * Four _Static_assert guards verify that the FIPS 203 ML-KEM-768 byte-size
 * constants in api.h match the NIST standard values. If params.h is ever
 * accidentally modified, the build will fail with a descriptive error message
 * rather than silently producing a binary with incorrect buffer sizes.
 *
 * MEMORY CONTRACT
 * ---------------
 * Callers MUST call mlkem_zeroize(ptr, size) on any buffer that held a
 * secret key (sk, 2400 bytes) or a shared secret (ss, 32 bytes) BEFORE
 * calling mlkem_free(ptr). mlkem_free does NOT zeroize.
 *
 * Failing to zeroize before free may leave sensitive key material in the
 * WASM linear memory, where it could be inspected via Module.HEAPU8 before
 * the allocator reuses the region.
 *
 * See wasm_export.c for the fully documented production version of these
 * exports, and docs/API.md for the JavaScript-level interface description.
 *
 * Reference: NIST FIPS 203, §7 (ML-KEM.KeyGen, Encaps, Decaps).
 */

#include <emscripten.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>

#include "api.h"
#include "fips202.h"

/*
 * Compile-time assertions: strictly enforce FIPS 203 byte lengths.
 *
 * If any of these fail, the build stops with a descriptive error.
 * Do NOT remove or weaken these — a mismatch would produce a WASM binary
 * whose exported buffer-size constants differ from the KEM implementation,
 * causing silent memory corruption or incorrect cryptographic operations.
 */
_Static_assert(PQCLEAN_MLKEM768_CLEAN_CRYPTO_PUBLICKEYBYTES == 1184,
    "FIPS 203 ML-KEM-768 public key size must be 1184 bytes");
_Static_assert(PQCLEAN_MLKEM768_CLEAN_CRYPTO_CIPHERTEXTBYTES == 1088,
    "FIPS 203 ML-KEM-768 ciphertext size must be 1088 bytes");
_Static_assert(PQCLEAN_MLKEM768_CLEAN_CRYPTO_SECRETKEYBYTES == 2400,
    "FIPS 203 ML-KEM-768 secret key size must be 2400 bytes");
_Static_assert(PQCLEAN_MLKEM768_CLEAN_CRYPTO_BYTES == 32,
    "FIPS 203 ML-KEM-768 shared secret size must be 32 bytes");

/* ── Memory Management ───────────────────────────────────────────────────── */

/**
 * mlkem_malloc — allocate n bytes in the WASM heap.
 *
 * Thin wrapper over malloc(). All ML-KEM key and ciphertext buffers should
 * be allocated through this symbol so that heap profiles can easily identify
 * PQC-related allocations. Returns NULL on failure.
 */
EMSCRIPTEN_KEEPALIVE
void *mlkem_malloc(size_t n) {
    return malloc(n);
}

/**
 * mlkem_free — release a heap buffer previously allocated by mlkem_malloc.
 *
 * CONTRACT: Callers MUST call mlkem_zeroize(ptr, size) BEFORE mlkem_free
 * for any buffer that held secret key material (sk) or a shared secret (ss).
 * mlkem_free does NOT zeroize. Passing NULL is a safe no-op.
 */
EMSCRIPTEN_KEEPALIVE
void mlkem_free(void *ptr) {
    if (ptr) free(ptr);
}

/**
 * mlkem_zeroize — securely overwrite n bytes starting at ptr with zeros.
 *
 * Uses a volatile pointer to prevent the compiler from eliding the write
 * as dead-store elimination. Call this on every buffer containing secret
 * key material or a shared secret before calling mlkem_free.
 *
 * Passing ptr=NULL or n=0 is a safe no-op.
 */
EMSCRIPTEN_KEEPALIVE
void mlkem_zeroize(void *ptr, size_t n) {
    if (ptr && n) {
        volatile unsigned char *p = (volatile unsigned char *)ptr;
        while (n--) *p++ = 0;
    }
}

/* ── FIPS 203 ML-KEM-768 Core Operations ────────────────────────────────── */

/**
 * mlkem_keypair — ML-KEM-768 key pair generation.
 *
 * @param[out] pk  1184-byte output buffer for the public key.
 * @param[out] sk  2400-byte output buffer for the secret key.
 *                 MUST be zeroized by the caller after use.
 * @return 0 on success; non-zero if the CSPRNG fails.
 */
EMSCRIPTEN_KEEPALIVE
int mlkem_keypair(uint8_t *pk, uint8_t *sk) {
    return PQCLEAN_MLKEM768_CLEAN_crypto_kem_keypair(pk, sk);
}

/**
 * mlkem_enc — ML-KEM-768 encapsulation.
 *
 * @param[out] ct  1088-byte output buffer for the ciphertext.
 * @param[out] ss  32-byte output buffer for the shared secret.
 *                 MUST be zeroized by the caller after use.
 * @param[in]  pk  1184-byte input public key.
 * @return 0 on success; non-zero if the CSPRNG fails.
 */
EMSCRIPTEN_KEEPALIVE
int mlkem_enc(uint8_t *ct, uint8_t *ss, const uint8_t *pk) {
    return PQCLEAN_MLKEM768_CLEAN_crypto_kem_enc(ct, ss, pk);
}

/**
 * mlkem_dec — ML-KEM-768 decapsulation.
 *
 * On an invalid ciphertext, ss receives a pseudo-random rejection value
 * (Fujisaki-Okamoto implicit rejection); the function does not signal failure.
 *
 * @param[out] ss  32-byte output buffer for the shared secret.
 *                 MUST be zeroized by the caller after use.
 * @param[in]  ct  1088-byte input ciphertext.
 * @param[in]  sk  2400-byte input secret key.
 *                 MUST be zeroized by the caller after use.
 * @return Always 0.
 */
EMSCRIPTEN_KEEPALIVE
int mlkem_dec(uint8_t *ss, const uint8_t *ct, const uint8_t *sk) {
    return PQCLEAN_MLKEM768_CLEAN_crypto_kem_dec(ss, ct, sk);
}

/* ── Supplemental FIPS 202 Hash Functions ───────────────────────────────── */

/**
 * sha3_256_wasm — SHA3-256 hash (FIPS 202).
 *
 * @param[out] out    32-byte output buffer.
 * @param[in]  in     Input message.
 * @param[in]  inlen  Length of input in bytes.
 */
EMSCRIPTEN_KEEPALIVE
void sha3_256_wasm(uint8_t *out, const uint8_t *in, size_t inlen) {
    sha3_256(out, in, inlen);
}

/**
 * sha3_512_wasm — SHA3-512 hash (FIPS 202).
 *
 * @param[out] out    64-byte output buffer.
 * @param[in]  in     Input message.
 * @param[in]  inlen  Length of input in bytes.
 */
EMSCRIPTEN_KEEPALIVE
void sha3_512_wasm(uint8_t *out, const uint8_t *in, size_t inlen) {
    sha3_512(out, in, inlen);
}

/**
 * shake256_wasm — SHAKE256 extendable-output function (XOF, FIPS 202).
 *
 * @param[out] out     Output buffer.
 * @param[in]  outlen  Requested output length in bytes.
 * @param[in]  in      Input message.
 * @param[in]  inlen   Length of input in bytes.
 */
EMSCRIPTEN_KEEPALIVE
void shake256_wasm(uint8_t *out, size_t outlen, const uint8_t *in, size_t inlen) {
    shake256(out, outlen, in, inlen);
}
