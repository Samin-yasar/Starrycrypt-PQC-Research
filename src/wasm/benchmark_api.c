#include <emscripten.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>

#include "api.h"
#include "fips202.h"

/* 
 * Compile-time assertions to strictly enforce FIPS 203 byte lengths.
 * If the underlying PQClean implementation or params.h ever drift
 * from the finalized standard, the WASM build will explicitly fail.
 */
_Static_assert(PQCLEAN_MLKEM768_CLEAN_CRYPTO_PUBLICKEYBYTES == 1184, "FIPS 203 ML-KEM-768 public key size must be 1184 bytes");
_Static_assert(PQCLEAN_MLKEM768_CLEAN_CRYPTO_CIPHERTEXTBYTES == 1088, "FIPS 203 ML-KEM-768 ciphertext size must be 1088 bytes");
_Static_assert(PQCLEAN_MLKEM768_CLEAN_CRYPTO_SECRETKEYBYTES == 2400, "FIPS 203 ML-KEM-768 secret key size must be 2400 bytes");
_Static_assert(PQCLEAN_MLKEM768_CLEAN_CRYPTO_BYTES == 32, "FIPS 203 ML-KEM-768 shared secret size must be 32 bytes");

/* Memory Management */

EMSCRIPTEN_KEEPALIVE
void* mlkem_malloc(size_t n) { 
    return malloc(n); 
}

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
    if (ptr && n) {
        volatile unsigned char* p = (volatile unsigned char*)ptr;
        while (n--) *p++ = 0;
    }
}

/* FIPS 203 ML-KEM-768 Core Operations */

EMSCRIPTEN_KEEPALIVE
int mlkem_keypair(uint8_t* pk, uint8_t* sk) {
    /* pk requires 1184 bytes, sk requires 2400 bytes */
    return PQCLEAN_MLKEM768_CLEAN_crypto_kem_keypair(pk, sk);
}

EMSCRIPTEN_KEEPALIVE
int mlkem_enc(uint8_t* ct, uint8_t* ss, const uint8_t* pk) {
    /* ct requires 1088 bytes, ss requires 32 bytes, pk requires 1184 bytes */
    return PQCLEAN_MLKEM768_CLEAN_crypto_kem_enc(ct, ss, pk);
}

EMSCRIPTEN_KEEPALIVE
int mlkem_dec(uint8_t* ss, const uint8_t* ct, const uint8_t* sk) {
    /* ss requires 32 bytes, ct requires 1088 bytes, sk requires 2400 bytes */
    return PQCLEAN_MLKEM768_CLEAN_crypto_kem_dec(ss, ct, sk);
}

/* Supplemental FIPS 202 Hash Functions */

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
