/* WASM export wrapper for ML-KEM-768 (FIPS 203) + SHA3-256 */
#include <emscripten.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include "api.h"
#include "fips202.h"

EMSCRIPTEN_KEEPALIVE
void* mlkem_malloc(size_t n) { return malloc(n); }

/*
 * mlkem_free — plain allocator free. Does NOT zeroize.
 * CONTRACT: callers MUST call mlkem_zeroize(ptr, size) before mlkem_free
 * for any buffer that holds secret key material or shared secrets.
 * Failure to do so may leave sensitive data in the WASM heap.
 */
EMSCRIPTEN_KEEPALIVE
void mlkem_free(void* ptr) {
    if (ptr) free(ptr);
}

EMSCRIPTEN_KEEPALIVE
void mlkem_zeroize(void* ptr, size_t n) {
    if (ptr && n) memset(ptr, 0, n);
}

EMSCRIPTEN_KEEPALIVE
int mlkem_keypair(uint8_t* pk, uint8_t* sk) {
    return PQCLEAN_MLKEM768_CLEAN_crypto_kem_keypair(pk, sk);
}

EMSCRIPTEN_KEEPALIVE
int mlkem_enc(uint8_t* ct, uint8_t* ss, const uint8_t* pk) {
    return PQCLEAN_MLKEM768_CLEAN_crypto_kem_enc(ct, ss, pk);
}

EMSCRIPTEN_KEEPALIVE
int mlkem_dec(uint8_t* ss, const uint8_t* ct, const uint8_t* sk) {
    return PQCLEAN_MLKEM768_CLEAN_crypto_kem_dec(ss, ct, sk);
}

EMSCRIPTEN_KEEPALIVE
void sha3_256_wasm(uint8_t* out, const uint8_t* in, size_t inlen) {
    sha3_256(out, in, inlen);
}

EMSCRIPTEN_KEEPALIVE
void sha3_512_wasm(uint8_t* out, const uint8_t* in, size_t inlen) {
    sha3_512(out, in, inlen);
}

EMSCRIPTEN_KEEPALIVE
void shake256_wasm(uint8_t* out, size_t outlen, const uint8_t* in, size_t inlen) {
    shake256(out, outlen, in, inlen);
}
