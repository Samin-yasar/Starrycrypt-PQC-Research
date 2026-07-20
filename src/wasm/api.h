/**
 * @file api.h
 * @brief Public C API for ML-KEM-768 (FIPS 203).
 *
 * This header declares the three core KEM operations:
 *   - Key generation  (crypto_kem_keypair)
 *   - Encapsulation   (crypto_kem_enc)
 *   - Decapsulation   (crypto_kem_dec)
 *
 * Naming follows the PQClean convention:
 *   PQCLEAN_{ALGORITHM}_{IMPLEMENTATION}_crypto_kem_{operation}
 *
 * This file intentionally avoids including params.h so that consumers can
 * use the API with the concrete byte-size constants defined here, without
 * depending on the internal parameterization. The constants are
 * authoritative and must match FIPS 203 Table 2 (ML-KEM-768 column).
 *
 * Reference: NIST FIPS 203, Section 7.1 (ML-KEM.KeyGen),
 *            7.2 (ML-KEM.Encaps), 7.3 (ML-KEM.Decaps).
 */

#ifndef PQCLEAN_MLKEM768_CLEAN_API_H
#define PQCLEAN_MLKEM768_CLEAN_API_H

#include <stdint.h>

/** Public key size in bytes (FIPS 203 Table 2). */
#define PQCLEAN_MLKEM768_CLEAN_CRYPTO_SECRETKEYBYTES  2400

/** Secret key size in bytes (FIPS 203 Table 2). */
#define PQCLEAN_MLKEM768_CLEAN_CRYPTO_PUBLICKEYBYTES  1184

/** Ciphertext size in bytes (FIPS 203 Table 2). */
#define PQCLEAN_MLKEM768_CLEAN_CRYPTO_CIPHERTEXTBYTES 1088

/** Shared secret size in bytes (FIPS 203 Table 2). */
#define PQCLEAN_MLKEM768_CLEAN_CRYPTO_BYTES           32

/** Algorithm name string. */
#define PQCLEAN_MLKEM768_CLEAN_CRYPTO_ALGNAME "ML-KEM-768"

/**
 * @brief ML-KEM-768 key pair generation (ML-KEM.KeyGen).
 *
 * Generates a public/secret key pair using fresh randomness from the
 * platform CSPRNG (randombytes). Internally calls keypair_derand with
 * 2*KYBER_SYMBYTES = 64 bytes of entropy split into key seed (d) and
 * implicit-rejection seed (z). Entropy is zeroized from the stack before
 * the function returns.
 *
 * @param[out] pk  Pointer to a caller-allocated buffer of at least
 *                 PQCLEAN_MLKEM768_CLEAN_CRYPTO_PUBLICKEYBYTES (1184) bytes.
 *                 Receives the serialized public key on success.
 * @param[out] sk  Pointer to a caller-allocated buffer of at least
 *                 PQCLEAN_MLKEM768_CLEAN_CRYPTO_SECRETKEYBYTES (2400) bytes.
 *                 Receives the serialized secret key on success.
 *                 The caller MUST zeroize this buffer after use.
 *
 * @return 0 on success. This function cannot fail under normal conditions;
 *         a non-zero return indicates a CSPRNG failure.
 */
int PQCLEAN_MLKEM768_CLEAN_crypto_kem_keypair(uint8_t *pk, uint8_t *sk);

/**
 * @brief ML-KEM-768 encapsulation (ML-KEM.Encaps).
 *
 * Generates a fresh ciphertext and the corresponding shared secret for
 * a given public key. The shared secret is uniformly random from the
 * perspective of anyone who does not know the corresponding secret key.
 *
 * @param[out] ct  Pointer to a caller-allocated buffer of at least
 *                 PQCLEAN_MLKEM768_CLEAN_CRYPTO_CIPHERTEXTBYTES (1088) bytes.
 *                 Receives the ciphertext on success.
 * @param[out] ss  Pointer to a caller-allocated buffer of at least
 *                 PQCLEAN_MLKEM768_CLEAN_CRYPTO_BYTES (32) bytes.
 *                 Receives the shared secret on success.
 *                 The caller MUST zeroize this buffer after use.
 * @param[in]  pk  Pointer to a valid public key of exactly
 *                 PQCLEAN_MLKEM768_CLEAN_CRYPTO_PUBLICKEYBYTES (1184) bytes.
 *
 * @return 0 on success. A non-zero return indicates a CSPRNG failure.
 */
int PQCLEAN_MLKEM768_CLEAN_crypto_kem_enc(uint8_t *ct, uint8_t *ss, const uint8_t *pk);

/**
 * @brief ML-KEM-768 decapsulation (ML-KEM.Decaps).
 *
 * Recovers the shared secret from a ciphertext and the corresponding
 * secret key. If the ciphertext is invalid (modified, replayed, or
 * otherwise malformed), the function returns a pseudo-random value
 * derived from the secret rejection seed z and the ciphertext, rather
 * than an error. This is the Fujisaki-Okamoto implicit-rejection mechanism
 * and is mandatory for IND-CCA2 security.
 *
 * This function MUST NOT return different values depending on whether
 * decapsulation succeeds or fails (no ciphertext-validity oracle).
 * The constant-time comparison in verify.c enforces this property.
 *
 * @param[out] ss  Pointer to a caller-allocated buffer of at least
 *                 PQCLEAN_MLKEM768_CLEAN_CRYPTO_BYTES (32) bytes.
 *                 Receives the shared secret (or pseudo-random rejection
 *                 value if ct is invalid).
 *                 The caller MUST zeroize this buffer after use.
 * @param[in]  ct  Pointer to a ciphertext of exactly
 *                 PQCLEAN_MLKEM768_CLEAN_CRYPTO_CIPHERTEXTBYTES (1088) bytes.
 * @param[in]  sk  Pointer to a secret key of exactly
 *                 PQCLEAN_MLKEM768_CLEAN_CRYPTO_SECRETKEYBYTES (2400) bytes.
 *                 The caller MUST zeroize this buffer after use.
 *
 * @return Always 0. The return value is retained for API consistency;
 *         it does not distinguish valid from invalid ciphertexts.
 */
int PQCLEAN_MLKEM768_CLEAN_crypto_kem_dec(uint8_t *ss, const uint8_t *ct, const uint8_t *sk);

#endif /* PQCLEAN_MLKEM768_CLEAN_API_H */
