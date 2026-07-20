/**
 * @file params.h
 * @brief ML-KEM-768 (FIPS 203) parameter set definitions.
 *
 * This header defines all compile-time parameters for the ML-KEM-768 instance
 * of the Module-Lattice Key Encapsulation Mechanism (FIPS 203). Parameter values
 * are fixed; they must not be altered without invalidating FIPS 203 compliance.
 *
 * Reference: NIST FIPS 203, "Module-Lattice-Based Key-Encapsulation Mechanism
 *            Standard," August 2024. Table 2 (ML-KEM-768 column).
 *
 * Naming note: Internal macros use the "KYBER_*" prefix inherited from the
 * PQClean reference implementation. The external public API (api.h) uses the
 * FIPS-mandated "PQCLEAN_MLKEM768_CLEAN_*" naming. Do not conflate the two.
 *
 * With KYBER_K=3 the derived buffer sizes are:
 *   Public key  = K * POLYBYTES + SYMBYTES = 3 * 384 + 32 = 1184 bytes
 *   Secret key  = K * POLYBYTES + pk + H(pk) + z
 *               = 1152 + 1184 + 32 + 32 = 2400 bytes
 *   Ciphertext  = K * POLYVECCOMPRESSED + POLYCOMPRESSED
 *               = 3 * 320 + 128 = 1088 bytes
 *   Shared sec. = 32 bytes
 */

#ifndef PQCLEAN_MLKEM768_CLEAN_PARAMS_H
#define PQCLEAN_MLKEM768_CLEAN_PARAMS_H

/*
 * KYBER_N — polynomial degree.
 * The ring is R_q = Z_q[X] / (X^N + 1).
 * N=256 is required by FIPS 203 for all ML-KEM parameter sets.
 */
#define KYBER_N 256

/*
 * KYBER_Q — modulus.
 * q=3329 is a prime satisfying q ≡ 1 (mod 2N), which ensures that N-th
 * roots of unity exist in Z_q, enabling the NTT.
 */
#define KYBER_Q 3329

/*
 * KYBER_SYMBYTES — size of seeds, hashes, and the shared secret (bytes).
 * Used as the length of: random seeds d and z, H(pk), G output halves,
 * PRF/KDF outputs.
 */
#define KYBER_SYMBYTES 32

/*
 * KYBER_SSBYTES — shared secret size (bytes).
 * Equals KYBER_SYMBYTES. Named separately for clarity in KEM API.
 */
#define KYBER_SSBYTES  32

/*
 * KYBER_POLYBYTES — serialized size of one polynomial (bytes).
 * Each of the N=256 coefficients is in Z_q (< 3329, fits in 12 bits).
 * Packed as 256 * 12 bits / 8 = 384 bytes.
 */
#define KYBER_POLYBYTES     384

/*
 * KYBER_POLYVECBYTES — serialized size of a K-length polynomial vector.
 */
#define KYBER_POLYVECBYTES  (KYBER_K * KYBER_POLYBYTES)

/*
 * KYBER_K — module rank (security parameter selector).
 * K=3 selects the ML-KEM-768 instance (NIST Level 3, ~192-bit classical
 * and ~108-bit post-quantum security).
 *
 * DO NOT CHANGE. Altering K without updating all size-derived macros
 * below will silently produce an incompatible, non-standard implementation.
 */
#define KYBER_K 3

/*
 * KYBER_ETA1 — noise distribution parameter for key generation.
 * The secret and error polynomials in KeyGen are sampled from CBD(η₁).
 * η₁=2 means each coefficient is the difference of two Binomial(η₁, 1/2)
 * samples, giving a CBD with σ² = η₁/2 = 1 and support [-2, 2].
 */
#define KYBER_ETA1 2

/*
 * KYBER_POLYCOMPRESSEDBYTES — compressed size of one polynomial in ciphertext.
 * For ML-KEM-768 the second ciphertext component (v polynomial) is
 * compressed to 128 bytes using 4 bits per coefficient.
 */
#define KYBER_POLYCOMPRESSEDBYTES    128

/*
 * KYBER_POLYVECCOMPRESSEDBYTES — compressed size of the polynomial vector
 * (first ciphertext component, u).
 * Each of the K=3 polynomials is compressed to 320 bytes (10 bits/coeff).
 * Total: 3 * 320 = 960 bytes.
 */
#define KYBER_POLYVECCOMPRESSEDBYTES (KYBER_K * 320)

/*
 * KYBER_ETA2 — noise distribution parameter for encapsulation.
 * The error polynomials in Encrypt_IND-CPA are sampled from CBD(η₂).
 * η₂=2, same as η₁ for the K=3 (768) instance.
 */
#define KYBER_ETA2 2

/* ----- Derived IND-CPA PKE sizes (internal) ----- */

/** IND-CPA message size = SYMBYTES = 32 bytes. */
#define KYBER_INDCPA_MSGBYTES       (KYBER_SYMBYTES)

/** IND-CPA public key = serialized polynomial vector t + seed ρ. */
#define KYBER_INDCPA_PUBLICKEYBYTES (KYBER_POLYVECBYTES + KYBER_SYMBYTES)

/** IND-CPA secret key = serialized polynomial vector s. */
#define KYBER_INDCPA_SECRETKEYBYTES (KYBER_POLYVECBYTES)

/** IND-CPA ciphertext = compressed u vector + compressed v polynomial. */
#define KYBER_INDCPA_BYTES          (KYBER_POLYVECCOMPRESSEDBYTES + KYBER_POLYCOMPRESSEDBYTES)

/* ----- KEM (CCA-secure) byte sizes (public API) ----- */

/**
 * KYBER_PUBLICKEYBYTES — public key size for ML-KEM-768 (bytes).
 * = 3 * 384 + 32 = 1184 bytes. Matches PQCLEAN_MLKEM768_CLEAN_CRYPTO_PUBLICKEYBYTES.
 */
#define KYBER_PUBLICKEYBYTES  (KYBER_INDCPA_PUBLICKEYBYTES)

/**
 * KYBER_SECRETKEYBYTES — secret key size for ML-KEM-768 (bytes).
 * = IND-CPA sk (1152) + pk (1184) + H(pk) (32) + z (32) = 2400 bytes.
 * The extra fields (pk, H(pk), z) are appended by the FO transform to
 * enable implicit rejection and multi-target countermeasure.
 */
#define KYBER_SECRETKEYBYTES  (KYBER_INDCPA_SECRETKEYBYTES \
                               + KYBER_INDCPA_PUBLICKEYBYTES \
                               + 2 * KYBER_SYMBYTES)

/**
 * KYBER_CIPHERTEXTBYTES — ciphertext size for ML-KEM-768 (bytes).
 * = 960 (u, compressed) + 128 (v, compressed) = 1088 bytes.
 */
#define KYBER_CIPHERTEXTBYTES (KYBER_INDCPA_BYTES)

#endif /* PQCLEAN_MLKEM768_CLEAN_PARAMS_H */
