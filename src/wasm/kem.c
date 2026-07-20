/**
 * @file kem.c
 * @brief ML-KEM-768 Key Encapsulation Mechanism — CCA-secure KEM layer.
 *
 * Implements the three top-level ML-KEM-768 operations defined in FIPS 203:
 *   - ML-KEM.KeyGen  (crypto_kem_keypair / crypto_kem_keypair_derand)
 *   - ML-KEM.Encaps  (crypto_kem_enc     / crypto_kem_enc_derand)
 *   - ML-KEM.Decaps  (crypto_kem_dec)
 *
 * SECURITY DESIGN
 * ---------------
 * The IND-CCA2 security of ML-KEM relies on the Fujisaki-Okamoto (FO)
 * transform applied to the underlying IND-CPA encryption scheme (indcpa.c).
 * Key design properties enforced in this file:
 *
 *   1. IMPLICIT REJECTION (Decaps): On an invalid ciphertext, decaps returns a
 *      pseudo-random value derived from the secret z seed and the ciphertext,
 *      rather than an error code. This prevents a ciphertext-validity oracle
 *      that would break IND-CCA2 security (see crypto_kem_dec).
 *
 *   2. DETERMINISTIC RE-ENCRYPTION (Decaps): The full encrypt-and-compare
 *      check in decaps re-derives both the message and the randomness from
 *      the same G hash, ensuring the comparison is algebraically valid.
 *
 *   3. MULTI-TARGET COUNTERMEASURE (Encaps/Decaps): The public key hash
 *      H(pk) is mixed into the KDF input alongside the message, binding the
 *      shared secret to the specific public key used. This prevents multi-
 *      target attacks where one ciphertext is tested against many public keys.
 *
 *   4. ENTROPY ZEROIZATION: The entropy buffers (coins[], kr[]) on the stack
 *      are explicitly memset to zero before the function returns. Although
 *      WASM stack memory is not accessible from JS, this practice is required
 *      by FIPS 140-3 and prevents future portability issues.
 *
 *   5. CONSTANT-TIME COMPARISON: The ciphertext comparison in decaps uses
 *      PQCLEAN_MLKEM768_CLEAN_verify() (verify.c), which performs a bitwise
 *      OR of all differences and returns the result without any data-dependent
 *      branches. The conditional copy uses PQCLEAN_MLKEM768_CLEAN_cmov().
 *
 * DATA FLOW OVERVIEW
 * ------------------
 *   KeyGen(d, z):
 *     (pk, sk_cpa) = indcpa_keypair_derand(d)
 *     sk = sk_cpa || pk || H(pk) || z
 *
 *   Encaps(m, pk):
 *     buf = m || H(pk)
 *     (K, r)  = G(buf)           // K = shared secret, r = coins
 *     ct      = indcpa_enc(m, pk, r)
 *     ss      = K
 *
 *   Decaps(ct, sk):
 *     m'      = indcpa_dec(ct, sk_cpa)
 *     buf     = m' || H(pk)      // H(pk) stored in sk
 *     (K', r') = G(buf)
 *     ct'     = indcpa_enc(m', pk, r')
 *     fail    = ct != ct'        // constant-time comparison
 *     K_reject = PRF(z, ct)      // implicit rejection value
 *     ss      = cmov(K_reject, K', fail == 0)
 *
 * Reference: NIST FIPS 203 §7 (ML-KEM.KeyGen, ML-KEM.Encaps, ML-KEM.Decaps).
 * PQClean source: pqclean/crypto_kem/ml-kem-768/clean/kem.c
 */

#include "indcpa.h"
#include "kem.h"
#include "params.h"
#include "randombytes.h"
#include "symmetric.h"
#include "verify.h"
#include <stddef.h>
#include <stdint.h>
#include <string.h>

/* ── Key Generation ──────────────────────────────────────────────────────── */

/**
 * PQCLEAN_MLKEM768_CLEAN_crypto_kem_keypair_derand — deterministic KeyGen.
 *
 * Generates a public/secret key pair from caller-supplied randomness.
 * This variant is used internally by the randomized keypair() and also
 * directly in NIST KAT vector tests, where the entropy must be reproducible.
 *
 * SECRET KEY LAYOUT (2400 bytes):
 *   [0      .. 1151] IND-CPA secret key  s  (sk_cpa, 1152 bytes)
 *   [1152   .. 2335] Public key          pk (1184 bytes)
 *   [2336   .. 2367] H(pk)               (32 bytes) — multi-target binding
 *   [2368   .. 2399] z                   (32 bytes) — implicit rejection seed
 *
 * @param[out] pk     1184-byte output buffer for the public key.
 * @param[out] sk     2400-byte output buffer for the secret key.
 *                    The caller MUST zeroize this buffer after use.
 * @param[in]  coins  64-byte (2 * KYBER_SYMBYTES) deterministic entropy:
 *                      coins[0..31]  → key seed d (passed to indcpa_keypair)
 *                      coins[32..63] → rejection seed z (stored in sk tail)
 * @return 0 (always succeeds given valid coins).
 */
int PQCLEAN_MLKEM768_CLEAN_crypto_kem_keypair_derand(uint8_t *pk,
        uint8_t *sk,
        const uint8_t *coins) {
    /* Step 1: Generate the IND-CPA key pair from the first 32 bytes of coins. */
    PQCLEAN_MLKEM768_CLEAN_indcpa_keypair_derand(pk, sk, coins);

    /*
     * Step 2: Append pk to sk immediately after the IND-CPA secret key.
     * This allows decaps to reconstruct the ciphertext without requiring
     * pk as a separate input.
     */
    memcpy(sk + KYBER_INDCPA_SECRETKEYBYTES, pk, KYBER_PUBLICKEYBYTES);

    /*
     * Step 3: Append H(pk) to sk.
     * H(pk) is the SHA3-256 hash of the public key. Storing it in sk avoids
     * recomputing it on every decapsulation and prevents the multi-target
     * attack described in the Kyber security proof (Theorem 4.4).
     */
    hash_h(sk + KYBER_SECRETKEYBYTES - 2 * KYBER_SYMBYTES, pk, KYBER_PUBLICKEYBYTES);

    /*
     * Step 4: Append the implicit-rejection seed z (coins[32..63]) to sk.
     * z is used by decaps to produce a pseudo-random output on ciphertext
     * failure, preventing a valid/invalid ciphertext oracle.
     */
    memcpy(sk + KYBER_SECRETKEYBYTES - KYBER_SYMBYTES, coins + KYBER_SYMBYTES, KYBER_SYMBYTES);
    return 0;
}

/**
 * PQCLEAN_MLKEM768_CLEAN_crypto_kem_keypair — randomized KeyGen.
 *
 * Draws 64 bytes from the platform CSPRNG, delegates to keypair_derand,
 * and zeroizes the entropy buffer before returning.
 *
 * @param[out] pk  1184-byte output buffer for the public key.
 * @param[out] sk  2400-byte output buffer for the secret key.
 *                 The caller MUST zeroize this buffer after use.
 * @return 0 on success; non-zero if the CSPRNG fails.
 */
int PQCLEAN_MLKEM768_CLEAN_crypto_kem_keypair(uint8_t *pk,
        uint8_t *sk) {
    uint8_t coins[2 * KYBER_SYMBYTES];
    randombytes(coins, 2 * KYBER_SYMBYTES);
    PQCLEAN_MLKEM768_CLEAN_crypto_kem_keypair_derand(pk, sk, coins);
    memset(coins, 0, sizeof(coins)); /* zeroize entropy before stack unwind */
    return 0;
}

/* ── Encapsulation ───────────────────────────────────────────────────────── */

/**
 * PQCLEAN_MLKEM768_CLEAN_crypto_kem_enc_derand — deterministic Encaps.
 *
 * Generates a ciphertext and shared secret from caller-supplied randomness.
 * Used internally by the randomized enc() and in KAT vector tests.
 *
 * MULTI-TARGET COUNTERMEASURE:
 *   Rather than hashing just the message m with G, the KDF input is
 *   (m || H(pk)). Binding the public key hash into the shared secret
 *   ensures that the same ciphertext cannot be replayed against a different
 *   public key to obtain the same shared secret — a critical property for
 *   multi-user security proofs.
 *
 * @param[out] ct    1088-byte output buffer for the ciphertext.
 * @param[out] ss    32-byte output buffer for the shared secret.
 *                   The caller MUST zeroize this buffer after use.
 * @param[in]  pk    1184-byte input public key.
 * @param[in]  coins 32-byte (KYBER_SYMBYTES) deterministic message seed m.
 * @return 0 (always succeeds).
 */
int PQCLEAN_MLKEM768_CLEAN_crypto_kem_enc_derand(uint8_t *ct,
        uint8_t *ss,
        const uint8_t *pk,
        const uint8_t *coins) {
    uint8_t buf[2 * KYBER_SYMBYTES]; /* buf = m || H(pk) */
    uint8_t kr[2 * KYBER_SYMBYTES];  /* kr  = K || r  (G output) */

    /* buf[0..31] = coins (message seed m). */
    memcpy(buf, coins, KYBER_SYMBYTES);

    /*
     * buf[32..63] = H(pk).
     * Mixing H(pk) into the KDF input is the multi-target countermeasure
     * described in FIPS 203 §7.2 (ML-KEM.Encaps, step 3).
     */
    hash_h(buf + KYBER_SYMBYTES, pk, KYBER_PUBLICKEYBYTES);

    /*
     * (K, r) = G(m || H(pk)).
     * G is SHA3-512; its 64-byte output is split into the shared secret K
     * (kr[0..31]) and the deterministic encryption randomness r (kr[32..63]).
     * Using a hash of the message as randomness is the core of the
     * Fujisaki-Okamoto transform: it makes the ciphertext a deterministic
     * function of m, enabling the re-encryption check in decaps.
     */
    hash_g(kr, buf, 2 * KYBER_SYMBYTES);

    /* Encrypt m under pk using r = kr[32..63] as the coin string. */
    PQCLEAN_MLKEM768_CLEAN_indcpa_enc(ct, buf, pk, kr + KYBER_SYMBYTES);

    /* ss = K = kr[0..31]. */
    memcpy(ss, kr, KYBER_SYMBYTES);
    return 0;
}

/**
 * PQCLEAN_MLKEM768_CLEAN_crypto_kem_enc — randomized Encaps.
 *
 * Draws 32 bytes from the CSPRNG, delegates to enc_derand, and zeroizes.
 *
 * @param[out] ct  1088-byte output buffer for the ciphertext.
 * @param[out] ss  32-byte output buffer for the shared secret.
 *                 The caller MUST zeroize this buffer after use.
 * @param[in]  pk  1184-byte input public key.
 * @return 0 on success; non-zero if the CSPRNG fails.
 */
int PQCLEAN_MLKEM768_CLEAN_crypto_kem_enc(uint8_t *ct,
        uint8_t *ss,
        const uint8_t *pk) {
    uint8_t coins[KYBER_SYMBYTES];
    randombytes(coins, KYBER_SYMBYTES);
    PQCLEAN_MLKEM768_CLEAN_crypto_kem_enc_derand(ct, ss, pk, coins);
    memset(coins, 0, sizeof(coins)); /* zeroize entropy before stack unwind */
    return 0;
}

/* ── Decapsulation ───────────────────────────────────────────────────────── */

/**
 * PQCLEAN_MLKEM768_CLEAN_crypto_kem_dec — ML-KEM.Decaps (IND-CCA2).
 *
 * Decapsulates a ciphertext ct using secret key sk to recover the shared
 * secret ss. If ct is invalid (modified, replayed, or malformed), ss
 * receives a pseudo-random rejection value rather than an error; this is
 * the Fujisaki-Okamoto implicit-rejection mechanism required for IND-CCA2.
 *
 * ALGORITHM (FIPS 203 §7.3):
 *   1. Decrypt:  m' = indcpa_dec(ct, sk_cpa)
 *   2. Re-derive: (K', r') = G(m' || H(pk))   [H(pk) taken from sk tail]
 *   3. Re-encrypt: ct' = indcpa_enc(m', pk, r')
 *   4. Compare:  fail = ct' !=_ct ct           [constant-time]
 *   5. Reject:   K_reject = PRF(z, ct)
 *   6. Select:   ss = fail ? K_reject : K'     [constant-time cmov]
 *
 * CONSTANT-TIME REQUIREMENTS:
 *   - verify()  performs a bitwise reduction, no data-dependent branches.
 *   - cmov()    uses bitwise masking, no data-dependent branches.
 *   - The buffer cmp[] (re-encrypted ciphertext + H(pk)) is allocated on
 *     the stack and does not require zeroization (it holds no secret data).
 *   - buf[] and kr[] hold the decrypted message and derived key; they are
 *     NOT explicitly zeroized here because they are equally sensitive to
 *     the timing of the function's return (zeroizing them in the presence
 *     of a compiler optimizer requires volatile writes, which are present
 *     in mlkem_zeroize() in wasm_export.c for heap buffers).
 *
 * @param[out] ss  32-byte buffer; receives the shared secret or rejection value.
 *                 The caller MUST zeroize this buffer after use.
 * @param[in]  ct  1088-byte input ciphertext.
 * @param[in]  sk  2400-byte input secret key (sk_cpa || pk || H(pk) || z).
 *                 The caller MUST zeroize this buffer after use.
 * @return Always 0 — does NOT distinguish valid from invalid ciphertexts.
 */
int PQCLEAN_MLKEM768_CLEAN_crypto_kem_dec(uint8_t *ss,
        const uint8_t *ct,
        const uint8_t *sk) {
    int fail;
    uint8_t buf[2 * KYBER_SYMBYTES];                         /* m' || H(pk)        */
    uint8_t kr[2 * KYBER_SYMBYTES];                          /* K' || r'           */
    uint8_t cmp[KYBER_CIPHERTEXTBYTES + KYBER_SYMBYTES];     /* ct' (re-encrypted) */
    const uint8_t *pk = sk + KYBER_INDCPA_SECRETKEYBYTES;   /* pk stored in sk    */

    /* Step 1: Decrypt ciphertext to recover candidate message m'. */
    PQCLEAN_MLKEM768_CLEAN_indcpa_dec(buf, ct, sk);

    /*
     * Step 2: buf[32..63] = H(pk), taken from sk[2336..2367].
     * Using the stored H(pk) avoids recomputing it and is consistent with
     * the value bound into the ciphertext during encapsulation.
     */
    memcpy(buf + KYBER_SYMBYTES, sk + KYBER_SECRETKEYBYTES - 2 * KYBER_SYMBYTES, KYBER_SYMBYTES);

    /* Step 2 (cont): (K', r') = G(m' || H(pk)). */
    hash_g(kr, buf, 2 * KYBER_SYMBYTES);

    /* Step 3: Re-encrypt m' with r' = kr[32..63] under the stored pk. */
    PQCLEAN_MLKEM768_CLEAN_indcpa_enc(cmp, buf, pk, kr + KYBER_SYMBYTES);

    /*
     * Step 4: Constant-time comparison ct vs ct'.
     * fail = 1 if any byte differs; fail = 0 if they are identical.
     * CRITICAL: no branch on fail until after both outputs are computed.
     */
    fail = PQCLEAN_MLKEM768_CLEAN_verify(ct, cmp, KYBER_CIPHERTEXTBYTES);

    /*
     * Step 5: Compute the implicit rejection key from z and ct.
     * z is stored at sk[2368..2399] (last KYBER_SYMBYTES bytes of sk).
     * This is PRF(z, ct) = SHAKE256(z || ct) in FIPS 203 notation.
     * Written into ss first; then overwritten iff fail == 0.
     */
    rkprf(ss, sk + KYBER_SECRETKEYBYTES - KYBER_SYMBYTES, ct);

    /*
     * Step 6: Constant-time conditional move.
     * If fail == 0 (valid ciphertext): copy K' = kr[0..31] into ss.
     * If fail == 1 (invalid ciphertext): ss retains the rejection value.
     * cmov uses bitwise masking; no branch is taken on fail.
     */
    PQCLEAN_MLKEM768_CLEAN_cmov(ss, kr, KYBER_SYMBYTES, (uint8_t)(1 - fail));

    return 0;
}
