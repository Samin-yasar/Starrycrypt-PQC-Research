/**
 * @file indcpa.c
 * @brief ML-KEM-768 IND-CPA public-key encryption scheme (Module-LWE core).
 *
 * Implements the inner IND-CPA encryption layer of ML-KEM-768 as specified in
 * FIPS 203 §5 (K-PKE). The KEM in kem.c wraps this layer with a Fujisaki-
 * Okamoto transform to achieve IND-CCA2 security.
 *
 * MATHEMATICAL BACKGROUND
 * -----------------------
 * All polynomial arithmetic is performed in the ring:
 *   R_q = Z_q[X] / (X^N + 1),  N = 256,  q = 3329.
 *
 * q = 3329 is a prime with q ≡ 1 (mod 2N), guaranteeing the existence of
 * a primitive 2N-th root of unity in Z_q. This enables the Number Theoretic
 * Transform (NTT), which reduces polynomial multiplication from O(N²) to
 * O(N log N) via the negacyclic NTT defined in FIPS 203 §4.3.
 *
 * Module-LWE security: keys and error vectors are sampled from the centered
 * binomial distribution CBD(η), giving each coefficient variance η/2 and
 * support [−η, η]. The computational hardness assumption is that, given A
 * and t = A·s + e, it is infeasible to recover s or distinguish t from
 * uniform.
 *
 * KEY GENERATION (indcpa_keypair_derand):
 *   coins    → hash_g(coins || K) → (ρ, σ)    [ρ = public seed, σ = noise seed]
 *   A        = gen_a(ρ)                         [K × K matrix over R_q, NTT domain]
 *   s, e     = CBD(σ, η₁)                       [secret vector, error vector]
 *   ŝ        = NTT(s);    ê = NTT(e)
 *   t̂        = A · ŝ + ê                        [NTT domain arithmetic]
 *   pk       = encode(t̂) || ρ
 *   sk_cpa   = encode(ŝ)
 *
 * ENCRYPTION (indcpa_enc):
 *   A^T      = gen_at(ρ)
 *   r, e₁, e₂ = CBD(coins, η₁/η₂)              [fresh randomness per encryption]
 *   r̂        = NTT(r)
 *   u        = INTT(A^T · r̂) + e₁              [u ∈ R_q^K]
 *   v        = INTT(t̂ · r̂) + e₂ + Decompress(m, 1)
 *   ct       = Compress(u, d_u) || Compress(v, d_v)
 *
 * DECRYPTION (indcpa_dec):
 *   (u, v)   = Decompress(ct)
 *   v - INTT(ŝ · NTT(u)) ≈ m + noise           [noise ≈ 0 if small]
 *   m        = Compress(v - INTT(ŝ · û), 1)
 *
 * MATRIX GENERATION (gen_matrix):
 *   Each entry A[i][j] is derived via:
 *     SHAKE128(ρ || j || i) → rejection sampling mod q
 *   Transposed sampling: swap i↔j indices for gen_at.
 *   The GEN_MATRIX_NBLOCKS constant is chosen so that one initial squeeze
 *   fills enough buffer for ≥ N valid coefficients with high probability,
 *   reducing the expected number of additional squeezes to < 1.
 *
 * Reference: NIST FIPS 203, §5 (K-PKE.KeyGen, K-PKE.Encrypt, K-PKE.Decrypt).
 * PQClean source: pqclean/crypto_kem/ml-kem-768/clean/indcpa.c
 */

#include "indcpa.h"
#include "ntt.h"
#include "params.h"
#include "poly.h"
#include "polyvec.h"
#include "randombytes.h"
#include "symmetric.h"
#include <stddef.h>
#include <stdint.h>
#include <string.h>

/* ── Serialization Helpers ───────────────────────────────────────────────── */

/**
 * pack_pk — serialize the IND-CPA public key.
 *
 * Encodes the public key as:
 *   r[0..POLYVECBYTES-1]         = polyvec_tobytes(pk)  (NTT-domain t̂)
 *   r[POLYVECBYTES..POLYVECBYTES+31] = seed ρ           (32-byte public seed)
 *
 * The seed ρ is transmitted alongside t̂ so the receiver can regenerate
 * the public matrix A = gen_a(ρ) without storing all K² polynomials.
 *
 * @param[out] r     KYBER_INDCPA_PUBLICKEYBYTES-byte output buffer.
 * @param[in]  pk    Input public polynomial vector (NTT domain, t̂).
 * @param[in]  seed  32-byte public seed ρ.
 */
static void pack_pk(uint8_t r[KYBER_INDCPA_PUBLICKEYBYTES],
                    polyvec *pk,
                    const uint8_t seed[KYBER_SYMBYTES]) {
    PQCLEAN_MLKEM768_CLEAN_polyvec_tobytes(r, pk);
    memcpy(r + KYBER_POLYVECBYTES, seed, KYBER_SYMBYTES);
}

/**
 * unpack_pk — deserialize the IND-CPA public key.
 *
 * Inverse of pack_pk. Recovers the NTT-domain polynomial vector t̂ and
 * the public seed ρ from the packed byte representation.
 *
 * @param[out] pk        Output public polynomial vector (NTT domain, t̂).
 * @param[out] seed      32-byte output buffer for the public seed ρ.
 * @param[in]  packedpk  Serialized public key (KYBER_INDCPA_PUBLICKEYBYTES bytes).
 */
static void unpack_pk(polyvec *pk,
                      uint8_t seed[KYBER_SYMBYTES],
                      const uint8_t packedpk[KYBER_INDCPA_PUBLICKEYBYTES]) {
    PQCLEAN_MLKEM768_CLEAN_polyvec_frombytes(pk, packedpk);
    memcpy(seed, packedpk + KYBER_POLYVECBYTES, KYBER_SYMBYTES);
}

/**
 * pack_sk — serialize the IND-CPA secret key.
 *
 * Encodes the NTT-domain secret polynomial vector ŝ as a flat byte array.
 * The IND-CPA secret key consists solely of ŝ; the full KEM secret key
 * (kem.c) appends pk, H(pk), and z to this.
 *
 * @param[out] r   KYBER_INDCPA_SECRETKEYBYTES-byte output buffer.
 * @param[in]  sk  Input secret polynomial vector (NTT domain, ŝ).
 */
static void pack_sk(uint8_t r[KYBER_INDCPA_SECRETKEYBYTES], polyvec *sk) {
    PQCLEAN_MLKEM768_CLEAN_polyvec_tobytes(r, sk);
}

/**
 * unpack_sk — deserialize the IND-CPA secret key.
 *
 * Inverse of pack_sk. Recovers the NTT-domain secret polynomial vector ŝ.
 *
 * @param[out] sk        Output secret polynomial vector (NTT domain, ŝ).
 * @param[in]  packedsk  Serialized IND-CPA secret key (KYBER_INDCPA_SECRETKEYBYTES bytes).
 */
static void unpack_sk(polyvec *sk, const uint8_t packedsk[KYBER_INDCPA_SECRETKEYBYTES]) {
    PQCLEAN_MLKEM768_CLEAN_polyvec_frombytes(sk, packedsk);
}

/**
 * pack_ciphertext — serialize the IND-CPA ciphertext.
 *
 * Encodes the ciphertext as:
 *   r[0..POLYVECCOMPRESSEDBYTES-1]         = Compress(u, d_u)  (960 bytes, 10 bits/coeff)
 *   r[POLYVECCOMPRESSEDBYTES..BYTES-1]     = Compress(v, d_v)  (128 bytes,  4 bits/coeff)
 *
 * The compression lossy-encodes u and v to reduce the ciphertext size,
 * trading a small noise increase (bounded by the compression rounding error)
 * for compactness. The parameters d_u and d_v are fixed by FIPS 203 Table 2.
 *
 * @param[out] r  KYBER_INDCPA_BYTES-byte output buffer.
 * @param[in]  b  First ciphertext component u (K polynomial vector in R_q).
 * @param[in]  v  Second ciphertext component v (single polynomial in R_q).
 */
static void pack_ciphertext(uint8_t r[KYBER_INDCPA_BYTES], polyvec *b, poly *v) {
    PQCLEAN_MLKEM768_CLEAN_polyvec_compress(r, b);
    PQCLEAN_MLKEM768_CLEAN_poly_compress(r + KYBER_POLYVECCOMPRESSEDBYTES, v);
}

/**
 * unpack_ciphertext — deserialize and decompress the IND-CPA ciphertext.
 *
 * Approximate inverse of pack_ciphertext. The decompression introduces a
 * small rounding error that is absorbed by the noise margins of the scheme.
 *
 * @param[out] b  Output first ciphertext component u.
 * @param[out] v  Output second ciphertext component v.
 * @param[in]  c  KYBER_INDCPA_BYTES-byte serialized ciphertext.
 */
static void unpack_ciphertext(polyvec *b, poly *v, const uint8_t c[KYBER_INDCPA_BYTES]) {
    PQCLEAN_MLKEM768_CLEAN_polyvec_decompress(b, c);
    PQCLEAN_MLKEM768_CLEAN_poly_decompress(v, c + KYBER_POLYVECCOMPRESSEDBYTES);
}

/* ── Rejection Sampling ──────────────────────────────────────────────────── */

/**
 * rej_uniform — rejection-sample uniform integers mod q from a byte buffer.
 *
 * Parses the input buffer in 3-byte groups, extracting two 12-bit values
 * per group:
 *   val0 = (buf[pos]   | (buf[pos+1] << 8)) & 0xFFF    [bits 0..11]
 *   val1 = (buf[pos+1] >> 4 | buf[pos+2] << 4) & 0xFFF [bits 12..23]
 *
 * Each value is accepted iff < q = 3329 (i.e., it lies in the range [0, q)).
 * Values ≥ 3329 are discarded (rejection). On average, 3328/4096 ≈ 81% of
 * 12-bit values are accepted, so approximately 1.23 × N bytes are needed
 * per polynomial. gen_matrix pre-computes GEN_MATRIX_NBLOCKS to hold ≥ N
 * values in expectation without requiring a second XOF squeeze call.
 *
 * @param[out] r       Output buffer; receives the accepted integer values.
 * @param[in]  len     Number of integers requested (at most KYBER_N = 256).
 * @param[in]  buf     Input byte buffer (uniform random bytes from XOF).
 * @param[in]  buflen  Length of the input buffer in bytes.
 * @return The number of integers written to r (≤ len).
 */
static unsigned int rej_uniform(int16_t *r,
                                unsigned int len,
                                const uint8_t *buf,
                                unsigned int buflen) {
    unsigned int ctr, pos;
    uint16_t val0, val1;

    ctr = pos = 0;
    while (ctr < len && pos + 3 <= buflen) {
        /* Extract two 12-bit values packed into 3 bytes. */
        val0 = ((buf[pos + 0] >> 0) | ((uint16_t)buf[pos + 1] << 8)) & 0xFFF;
        val1 = ((buf[pos + 1] >> 4) | ((uint16_t)buf[pos + 2] << 4)) & 0xFFF;
        pos += 3;

        if (val0 < KYBER_Q) {
            r[ctr++] = val0;
        }
        if (ctr < len && val1 < KYBER_Q) {
            r[ctr++] = val1;
        }
    }

    return ctr;
}

/*
 * gen_a(A, B)  — generate matrix A  (standard orientation)
 * gen_at(A, B) — generate matrix A^T (transposed; used in encryption)
 */
#define gen_a(A,B)  PQCLEAN_MLKEM768_CLEAN_gen_matrix(A,B,0)
#define gen_at(A,B) PQCLEAN_MLKEM768_CLEAN_gen_matrix(A,B,1)

/* ── Matrix Generation ───────────────────────────────────────────────────── */

/*
 * GEN_MATRIX_NBLOCKS — number of SHAKE128 output blocks squeezed initially.
 *
 * Chosen so that the initial squeeze produces enough bytes to fill all
 * KYBER_N = 256 polynomial coefficients with high probability via rejection
 * sampling, without requiring an additional squeeze call. The formula
 * accounts for the 12-bit packing efficiency and the rejection rate.
 */
#define GEN_MATRIX_NBLOCKS ((12*KYBER_N/8*(1 << 12)/KYBER_Q + XOF_BLOCKBYTES)/XOF_BLOCKBYTES)

/**
 * PQCLEAN_MLKEM768_CLEAN_gen_matrix — generate the public matrix A (or A^T).
 *
 * A is a K×K matrix of polynomials in R_q, sampled uniformly at random
 * from SHAKE128(ρ || j || i) using rejection sampling (rej_uniform above).
 * A is deterministic given the seed ρ and is implicitly public.
 *
 * INDEX CONVENTION:
 *   Standard (transposed=0): XOF is seeded with (ρ, j, i) → A[i][j]
 *   Transposed (transposed=1): XOF is seeded with (ρ, i, j) → A^T[i][j]
 *   This convention follows FIPS 203 §4.2.2.
 *
 * Not declared static to allow direct benchmarking of matrix generation.
 *
 * @param[out] a           K-element array of polyvec; receives the matrix rows.
 * @param[in]  seed        32-byte public seed ρ.
 * @param[in]  transposed  0 → generate A; 1 → generate A^T.
 */
void PQCLEAN_MLKEM768_CLEAN_gen_matrix(polyvec *a, const uint8_t seed[KYBER_SYMBYTES], int transposed) {
    unsigned int ctr, i, j;
    unsigned int buflen;
    uint8_t buf[GEN_MATRIX_NBLOCKS * XOF_BLOCKBYTES];
    xof_state state;

    for (i = 0; i < KYBER_K; i++) {
        for (j = 0; j < KYBER_K; j++) {
            /*
             * Seed the XOF with ρ and the (i, j) index pair.
             * Swapping (i, j) vs (j, i) generates A vs A^T respectively.
             */
            if (transposed) {
                xof_absorb(&state, seed, (uint8_t)i, (uint8_t)j);
            } else {
                xof_absorb(&state, seed, (uint8_t)j, (uint8_t)i);
            }

            /* Initial squeeze: enough bytes for ≥ N coefficients in expectation. */
            xof_squeezeblocks(buf, GEN_MATRIX_NBLOCKS, &state);
            buflen = GEN_MATRIX_NBLOCKS * XOF_BLOCKBYTES;
            ctr = rej_uniform(a[i].vec[j].coeffs, KYBER_N, buf, buflen);

            /*
             * If the initial blocks did not yield N accepted coefficients
             * (expected probability < 2%), squeeze one additional block at
             * a time until the polynomial is fully sampled.
             */
            while (ctr < KYBER_N) {
                xof_squeezeblocks(buf, 1, &state);
                buflen = XOF_BLOCKBYTES;
                ctr += rej_uniform(a[i].vec[j].coeffs + ctr, KYBER_N - ctr, buf, buflen);
            }
            xof_ctx_release(&state);
        }
    }
}

/* ── IND-CPA Key Generation ──────────────────────────────────────────────── */

/**
 * PQCLEAN_MLKEM768_CLEAN_indcpa_keypair_derand — deterministic IND-CPA KeyGen.
 *
 * Generates the IND-CPA key pair (pk, sk_cpa) from 32 bytes of entropy.
 * Called by the KEM layer (kem.c) with the first 32 bytes of its 64-byte
 * coin input.
 *
 * DERIVATION STEPS (FIPS 203 §5.1, K-PKE.KeyGen):
 *   1. (ρ, σ) = G(coins || K)  — expand the 32-byte seed into 64 bytes,
 *      appending the module rank K=3 as a domain separator to prevent
 *      cross-parameter attacks between ML-KEM-512/768/1024.
 *   2. A  = gen_a(ρ)           — public matrix (NTT domain).
 *   3. s  = CBD_η₁(σ, 0..K-1) — secret polynomial vector (from nonce 0..2).
 *   4. e  = CBD_η₁(σ, K..2K-1)— error polynomial vector (from nonce 3..5).
 *   5. ŝ  = NTT(s); ê = NTT(e)
 *   6. t̂  = A·ŝ + ê            — public key polynomial vector (NTT domain).
 *   7. pk  = encode(t̂) || ρ;   sk_cpa = encode(ŝ)
 *
 * @param[out] pk     KYBER_INDCPA_PUBLICKEYBYTES-byte output buffer.
 * @param[out] sk     KYBER_INDCPA_SECRETKEYBYTES-byte output buffer.
 * @param[in]  coins  KYBER_SYMBYTES (32) bytes of deterministic entropy.
 */
void PQCLEAN_MLKEM768_CLEAN_indcpa_keypair_derand(uint8_t pk[KYBER_INDCPA_PUBLICKEYBYTES],
        uint8_t sk[KYBER_INDCPA_SECRETKEYBYTES],
        const uint8_t coins[KYBER_SYMBYTES]) {
    unsigned int i;
    uint8_t buf[2 * KYBER_SYMBYTES]; /* (ρ, σ) from G expansion */
    const uint8_t *publicseed = buf;             /* ρ = buf[0..31]  */
    const uint8_t *noiseseed  = buf + KYBER_SYMBYTES; /* σ = buf[32..63] */
    uint8_t nonce = 0;
    polyvec a[KYBER_K], e, pkpv, skpv;

    /* Step 1: (ρ, σ) = G(coins || K). Append K=3 as domain separator. */
    memcpy(buf, coins, KYBER_SYMBYTES);
    buf[KYBER_SYMBYTES] = KYBER_K;
    hash_g(buf, buf, KYBER_SYMBYTES + 1);

    /* Step 2: Generate the public matrix A = gen_a(ρ) in NTT domain. */
    gen_a(a, publicseed);

    /* Step 3: Sample the secret vector s from CBD_η₁(σ, nonce = 0..K-1). */
    for (i = 0; i < KYBER_K; i++) {
        PQCLEAN_MLKEM768_CLEAN_poly_getnoise_eta1(&skpv.vec[i], noiseseed, nonce++);
    }
    /* Step 4: Sample the error vector e from CBD_η₁(σ, nonce = K..2K-1). */
    for (i = 0; i < KYBER_K; i++) {
        PQCLEAN_MLKEM768_CLEAN_poly_getnoise_eta1(&e.vec[i], noiseseed, nonce++);
    }

    /* Step 5: NTT-transform s and e. All subsequent arithmetic is in NTT domain. */
    PQCLEAN_MLKEM768_CLEAN_polyvec_ntt(&skpv);
    PQCLEAN_MLKEM768_CLEAN_polyvec_ntt(&e);

    /*
     * Step 6: t̂ = A · ŝ + ê  (matrix-vector multiplication in NTT domain).
     * basemul_acc_montgomery computes the inner product of row a[i] and ŝ
     * using Montgomery multiplication; poly_tomont converts the result to
     * Montgomery form before the addition.
     */
    for (i = 0; i < KYBER_K; i++) {
        PQCLEAN_MLKEM768_CLEAN_polyvec_basemul_acc_montgomery(&pkpv.vec[i], &a[i], &skpv);
        PQCLEAN_MLKEM768_CLEAN_poly_tomont(&pkpv.vec[i]);
    }

    PQCLEAN_MLKEM768_CLEAN_polyvec_add(&pkpv, &pkpv, &e);
    PQCLEAN_MLKEM768_CLEAN_polyvec_reduce(&pkpv);

    /* Step 7: Serialize sk_cpa = encode(ŝ), pk = encode(t̂) || ρ. */
    pack_sk(sk, &skpv);
    pack_pk(pk, &pkpv, publicseed);
}

/* ── IND-CPA Encryption ──────────────────────────────────────────────────── */

/**
 * PQCLEAN_MLKEM768_CLEAN_indcpa_enc — IND-CPA encryption (K-PKE.Encrypt).
 *
 * Encrypts a 32-byte message m under public key pk using randomness coins.
 * In the KEM context (kem.c), coins are derived from G(m || H(pk)) so that
 * the ciphertext is a deterministic function of m, enabling the re-encryption
 * check in decapsulation.
 *
 * DERIVATION STEPS (FIPS 203 §5.2, K-PKE.Encrypt):
 *   1. t̂, ρ = decode(pk)
 *   2. A^T  = gen_at(ρ)
 *   3. k    = Decompress(m, 1)   — 1-bit message encoding
 *   4. r    = CBD_η₁(coins, 0..K-1)
 *   5. e₁   = CBD_η₂(coins, K..2K-1)
 *   6. e₂   = CBD_η₂(coins, 2K)
 *   7. r̂    = NTT(r)
 *   8. u    = INTT(A^T · r̂) + e₁
 *   9. v    = INTT(t̂ · r̂) + e₂ + k
 *  10. ct   = Compress(u, d_u) || Compress(v, d_v)
 *
 * @param[out] c      KYBER_INDCPA_BYTES-byte ciphertext output.
 * @param[in]  m      KYBER_INDCPA_MSGBYTES (32) byte plaintext message.
 * @param[in]  pk     KYBER_INDCPA_PUBLICKEYBYTES byte public key.
 * @param[in]  coins  KYBER_SYMBYTES (32) byte randomness seed.
 */
void PQCLEAN_MLKEM768_CLEAN_indcpa_enc(uint8_t c[KYBER_INDCPA_BYTES],
                                       const uint8_t m[KYBER_INDCPA_MSGBYTES],
                                       const uint8_t pk[KYBER_INDCPA_PUBLICKEYBYTES],
                                       const uint8_t coins[KYBER_SYMBYTES]) {
    unsigned int i;
    uint8_t seed[KYBER_SYMBYTES];
    uint8_t nonce = 0;
    polyvec sp, pkpv, ep, at[KYBER_K], b;
    poly v, k, epp;

    /* Step 1: Decode t̂ and ρ from pk. */
    unpack_pk(&pkpv, seed, pk);

    /* Step 3: Encode 1-bit message into polynomial k. */
    PQCLEAN_MLKEM768_CLEAN_poly_frommsg(&k, m);

    /* Step 2: Generate A^T from ρ. */
    gen_at(at, seed);

    /* Steps 4-6: Sample randomness r, e₁, e₂ from CBD using coins. */
    for (i = 0; i < KYBER_K; i++) {
        PQCLEAN_MLKEM768_CLEAN_poly_getnoise_eta1(sp.vec + i, coins, nonce++);
    }
    for (i = 0; i < KYBER_K; i++) {
        PQCLEAN_MLKEM768_CLEAN_poly_getnoise_eta2(ep.vec + i, coins, nonce++);
    }
    PQCLEAN_MLKEM768_CLEAN_poly_getnoise_eta2(&epp, coins, nonce++);

    /* Step 7: r̂ = NTT(r). */
    PQCLEAN_MLKEM768_CLEAN_polyvec_ntt(&sp);

    /* Step 8: u = INTT(A^T · r̂) + e₁. */
    for (i = 0; i < KYBER_K; i++) {
        PQCLEAN_MLKEM768_CLEAN_polyvec_basemul_acc_montgomery(&b.vec[i], &at[i], &sp);
    }

    /* Step 9: v = INTT(t̂ · r̂) + e₂ + k. */
    PQCLEAN_MLKEM768_CLEAN_polyvec_basemul_acc_montgomery(&v, &pkpv, &sp);

    PQCLEAN_MLKEM768_CLEAN_polyvec_invntt_tomont(&b);
    PQCLEAN_MLKEM768_CLEAN_poly_invntt_tomont(&v);

    PQCLEAN_MLKEM768_CLEAN_polyvec_add(&b, &b, &ep);
    PQCLEAN_MLKEM768_CLEAN_poly_add(&v, &v, &epp);
    PQCLEAN_MLKEM768_CLEAN_poly_add(&v, &v, &k);
    PQCLEAN_MLKEM768_CLEAN_polyvec_reduce(&b);
    PQCLEAN_MLKEM768_CLEAN_poly_reduce(&v);

    /* Step 10: ct = Compress(u, d_u) || Compress(v, d_v). */
    pack_ciphertext(c, &b, &v);
}

/* ── IND-CPA Decryption ──────────────────────────────────────────────────── */

/**
 * PQCLEAN_MLKEM768_CLEAN_indcpa_dec — IND-CPA decryption (K-PKE.Decrypt).
 *
 * Recovers the 32-byte message m from ciphertext c using IND-CPA secret key sk.
 *
 * DERIVATION STEPS (FIPS 203 §5.3, K-PKE.Decrypt):
 *   1. (u, v) = Decompress(ct)
 *   2. ŝ = decode(sk)
 *   3. w = v - INTT(ŝ · NTT(u))   (cancel out the LWE error in expectation)
 *   4. m = Compress(w, 1)          (threshold decoding: round to {0, q/2})
 *
 * Note: This function is NOT constant-time with respect to the message m.
 * IND-CPA decryption does not require constant-time execution; the constant-
 * time requirement is imposed at the KEM (IND-CCA2) layer in kem.c, which
 * uses verify() and cmov() to avoid revealing whether re-encryption matched.
 *
 * @param[out] m   KYBER_INDCPA_MSGBYTES-byte output buffer for the message.
 * @param[in]  c   KYBER_INDCPA_BYTES-byte input ciphertext.
 * @param[in]  sk  KYBER_INDCPA_SECRETKEYBYTES-byte input IND-CPA secret key.
 */
void PQCLEAN_MLKEM768_CLEAN_indcpa_dec(uint8_t m[KYBER_INDCPA_MSGBYTES],
                                       const uint8_t c[KYBER_INDCPA_BYTES],
                                       const uint8_t sk[KYBER_INDCPA_SECRETKEYBYTES]) {
    polyvec b, skpv;
    poly v, mp;

    /* Step 1: Decompress (u, v) from ciphertext. */
    unpack_ciphertext(&b, &v, c);

    /* Step 2: Decode ŝ from sk. */
    unpack_sk(&skpv, sk);

    /*
     * Step 3: Compute w = v - INTT(ŝ · NTT(u)).
     *   NTT(u) = polyvec_ntt(b)   [in-place on b]
     *   ŝ · NTT(u) = basemul_acc_montgomery(mp, skpv, b)
     *   INTT(ŝ · NTT(u)) = poly_invntt_tomont(mp)
     *   w = poly_sub(v, mp) followed by poly_reduce
     */
    PQCLEAN_MLKEM768_CLEAN_polyvec_ntt(&b);
    PQCLEAN_MLKEM768_CLEAN_polyvec_basemul_acc_montgomery(&mp, &skpv, &b);
    PQCLEAN_MLKEM768_CLEAN_poly_invntt_tomont(&mp);

    PQCLEAN_MLKEM768_CLEAN_poly_sub(&mp, &v, &mp);
    PQCLEAN_MLKEM768_CLEAN_poly_reduce(&mp);

    /* Step 4: m = Compress(w, 1) — threshold rounding to recover bit message. */
    PQCLEAN_MLKEM768_CLEAN_poly_tomsg(m, &mp);
}
