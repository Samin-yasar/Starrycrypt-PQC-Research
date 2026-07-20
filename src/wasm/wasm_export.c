/**
 * @file wasm_export.c
 * @brief Emscripten KEEPALIVE export wrappers for ML-KEM-768 (FIPS 203).
 *
 * This file exposes a flat C API to the JavaScript layer via Emscripten's
 * ccall/cwrap mechanism. Each function is marked EMSCRIPTEN_KEEPALIVE so
 * the Emscripten linker does not dead-strip it even though it has no
 * in-tree callers.
 *
 * The exported symbols (prefixed with an underscore in WASM exports) are:
 *   Memory:     mlkem_malloc, mlkem_free, mlkem_zeroize
 *   ML-KEM-768: mlkem_keypair, mlkem_enc, mlkem_dec
 *   FIPS 202:   sha3_256_wasm, sha3_512_wasm, shake256_wasm
 *
 * Memory safety contract:
 *   Callers are required to call mlkem_zeroize(ptr, size) on any buffer
 *   containing secret key material (sk) or shared secrets (ss) BEFORE
 *   calling mlkem_free(ptr). mlkem_free does NOT zeroize.
 *
 * Compile-time assertions in this file enforce that the FIPS 203 ML-KEM-768
 * byte-size constants in api.h match the expected values from the standard.
 * If params.h is ever modified incorrectly, the WASM build will fail
 * explicitly with a descriptive error rather than silently producing an
 * incompatible binary.
 */

#include <emscripten.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>

#include "api.h"
#include "fips202.h"

/*
 * Compile-time assertions: enforce FIPS 203 ML-KEM-768 byte sizes.
 *
 * These assertions guard against accidental modification of params.h that
 * would silently break the JavaScript API (which hard-codes these sizes as
 * MLKEM_PUBLICKEYBYTES, etc.).  The build fails loudly rather than producing
 * a binary with wrong-sized operations.
 */
_Static_assert(PQCLEAN_MLKEM768_CLEAN_CRYPTO_PUBLICKEYBYTES  == 1184,
    "FIPS 203 ML-KEM-768 public key must be 1184 bytes");
_Static_assert(PQCLEAN_MLKEM768_CLEAN_CRYPTO_CIPHERTEXTBYTES == 1088,
    "FIPS 203 ML-KEM-768 ciphertext must be 1088 bytes");
_Static_assert(PQCLEAN_MLKEM768_CLEAN_CRYPTO_SECRETKEYBYTES  == 2400,
    "FIPS 203 ML-KEM-768 secret key must be 2400 bytes");
_Static_assert(PQCLEAN_MLKEM768_CLEAN_CRYPTO_BYTES           == 32,
    "FIPS 203 ML-KEM-768 shared secret must be 32 bytes");

/* ── Memory Management ───────────────────────────────────────────────────── */

/**
 * mlkem_malloc — allocate n bytes in the WASM heap.
 *
 * Thin wrapper around malloc(). Exported to JavaScript so that all heap
 * allocations for ML-KEM buffers go through this well-known symbol,
 * making them easy to identify in heap profiles.
 *
 * Returns NULL on allocation failure.
 */
EMSCRIPTEN_KEEPALIVE
void *mlkem_malloc(size_t n) {
    return malloc(n);
}

/**
 * mlkem_free — release a heap buffer previously allocated by mlkem_malloc.
 *
 * CONTRACT: The caller MUST call mlkem_zeroize(ptr, size) BEFORE mlkem_free
 * for any buffer that ever held secret key material (sk) or a shared secret
 * (ss). mlkem_free does NOT zeroize. Freeing without zeroizing may leave
 * sensitive data in the WASM linear memory where it could be read via
 * Module.HEAPU8 before the allocator reuses the region.
 *
 * Passing NULL is a no-op (matches free() behavior).
 */
EMSCRIPTEN_KEEPALIVE
void mlkem_free(void *ptr) {
    if (ptr) free(ptr);
}

/**
 * mlkem_zeroize — securely overwrite n bytes starting at ptr with zeros.
 *
 * Uses a volatile pointer to prevent the compiler from eliding the
 * memset as dead code when the buffer is about to be freed (a common
 * optimization that breaks secure memory erasure).
 *
 * Call this on every buffer containing secret key material or shared
 * secrets before calling mlkem_free.
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
 * Thin shim over PQCLEAN_MLKEM768_CLEAN_crypto_kem_keypair.
 * Exported to JavaScript as the primary key generation entry point.
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
 * Thin shim over PQCLEAN_MLKEM768_CLEAN_crypto_kem_enc.
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
 * Thin shim over PQCLEAN_MLKEM768_CLEAN_crypto_kem_dec.
 * On an invalid ciphertext, ss receives a pseudo-random rejection value
 * (the Fujisaki-Okamoto implicit rejection); the function does not fail.
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
/*
 * The following SHA-3 family functions are exported for use by the
 * JavaScript layer when it needs server-side hashing that is consistent
 * with the hash functions used internally by ML-KEM (e.g., H(pk)).
 * They delegate directly to the FIPS 202 implementations in fips202.c.
 */

/**
 * sha3_256_wasm — SHA3-256 hash.
 *
 * @param[out] out    32-byte output buffer.
 * @param[in]  in     Input message.
 * @param[in]  inlen  Length of input message in bytes.
 */
EMSCRIPTEN_KEEPALIVE
void sha3_256_wasm(uint8_t *out, const uint8_t *in, size_t inlen) {
    sha3_256(out, in, inlen);
}

/**
 * sha3_512_wasm — SHA3-512 hash.
 *
 * @param[out] out    64-byte output buffer.
 * @param[in]  in     Input message.
 * @param[in]  inlen  Length of input message in bytes.
 */
EMSCRIPTEN_KEEPALIVE
void sha3_512_wasm(uint8_t *out, const uint8_t *in, size_t inlen) {
    sha3_512(out, in, inlen);
}

/**
 * shake256_wasm — SHAKE256 extendable output function (XOF).
 *
 * @param[out] out     Output buffer.
 * @param[in]  outlen  Requested output length in bytes.
 * @param[in]  in      Input message.
 * @param[in]  inlen   Length of input message in bytes.
 */
EMSCRIPTEN_KEEPALIVE
void shake256_wasm(uint8_t *out, size_t outlen, const uint8_t *in, size_t inlen) {
    shake256(out, outlen, in, inlen);
}
