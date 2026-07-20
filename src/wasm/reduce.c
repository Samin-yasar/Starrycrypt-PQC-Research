/**
 * @file reduce.c
 * @brief Montgomery and Barrett modular reduction for ML-KEM-768 (q = 3329).
 *
 * Provides the two modular reduction routines used throughout the NTT and
 * polynomial arithmetic layers:
 *
 *   montgomery_reduce — converts a 32-bit Montgomery product back to a
 *                       16-bit representative mod q. Used after every
 *                       multiplication in the NTT and basemul routines.
 *
 *   barrett_reduce    — reduces a 16-bit value to a centered representative
 *                       in [-(q-1)/2, (q-1)/2]. Used after polynomial
 *                       additions and subtractions.
 *
 * MATHEMATICAL BACKGROUND
 * -----------------------
 * q = 3329 is the modulus for ML-KEM-768. All polynomial coefficients are
 * elements of Z_q = {0, 1, ..., 3328}.
 *
 * Montgomery Reduction:
 *   The NTT uses multiplication in Z_q, but computing a mod q after each
 *   multiply is expensive (requires a division). Montgomery form avoids
 *   the division by working with values scaled by a power of 2 (R = 2^16
 *   here). Given a 32-bit product a = x · y (in Montgomery form), the
 *   Montgomery reduction computes:
 *
 *     t = (a · q^{-1} mod R) cast to int16   [low 16 bits × QINV mod 2^16]
 *     result = (a - t · q) / R               [exact integer division by R]
 *
 *   The result is congruent to a · R^{-1} mod q and fits in 16 bits.
 *   QINV satisfies q · QINV ≡ 1 (mod 2^16), so QINV = q^{-1} mod 2^16.
 *   For q = 3329: QINV = 3327 (since 3329 × 3327 ≡ 1 mod 65536).
 *
 * Barrett Reduction:
 *   Reduces a 16-bit value a to the centered interval [-(q-1)/2, (q-1)/2]
 *   without a division, using an integer approximation of 1/q:
 *
 *     v ≈ round(2^26 / q)
 *     t = round(a · v / 2^26)  ≈ round(a / q)
 *     result = a - t · q
 *
 *   The rounding constant v = ((1 << 26) + q/2) / q ensures the approximation
 *   is correct for all |a| ≤ q · 2^{14} (well within 16-bit range).
 *
 * Reference: FIPS 203 §4 (modular arithmetic); Plantard, Susilo & Zhang
 *   "Improving NTT-based polynomial multiplication using montgomery reduction
 *   with an application lattice-based cryptography", 2012.
 */

#include "params.h"
#include "reduce.h"
#include <stdint.h>

/**
 * PQCLEAN_MLKEM768_CLEAN_montgomery_reduce — Montgomery modular reduction.
 *
 * Given a 32-bit integer a in the range [-q·2^15, q·2^15 - 1], computes a
 * 16-bit integer congruent to a · R^{-1} mod q, where R = 2^16.
 *
 * ALGORITHM:
 *   t = (int16_t)(a · QINV)         [low 16 bits of a multiplied by QINV]
 *   t = (a - t · q) >> 16           [exact: (a - t·q) is divisible by 2^16]
 *
 * The final result is in {-q+1, ..., q-1}, which fits in int16_t.
 *
 * USAGE: Called after every NTT butterfly multiplication to keep coefficients
 * in the valid range for subsequent additions without overflow.
 *
 * @param[in] a  32-bit input in [-q·2^15, q·2^15 - 1] = [-3329·32768, 3329·32767].
 * @return       16-bit integer in {-q+1, ..., q-1} ≡ a · R^{-1} (mod q).
 */
int16_t PQCLEAN_MLKEM768_CLEAN_montgomery_reduce(int32_t a) {
    int16_t t;

    /* t = low 16 bits of (a × QINV), interpreted as signed.
     * This is the Montgomery modular inverse step. */
    t = (int16_t)a * QINV;

    /* result = (a - t × q) / 2^16.
     * The subtraction cancels the low 16 bits, making the result
     * exactly divisible by R = 2^16; the right-shift is exact. */
    t = (a - (int32_t)t * KYBER_Q) >> 16;
    return t;
}

/**
 * PQCLEAN_MLKEM768_CLEAN_barrett_reduce — Barrett modular reduction.
 *
 * Reduces a 16-bit integer a to the centered representative mod q in
 * the range [-(q-1)/2, (q-1)/2] = [-1664, 1664], without a division.
 *
 * ALGORITHM (Barrett):
 *   v = round(2^26 / q)  = ((1 << 26) + q/2) / q   [compile-time constant]
 *   t = round(a * v / 2^26)   ≈ round(a / q)
 *   result = a - t * q
 *
 * The magic constant v is chosen so that the approximation error is at most
 * 1/2, guaranteeing |result| ≤ q/2 for all int16_t inputs.
 *
 * USAGE: Called after polyvec additions and subtractions to prevent
 * coefficient overflow before NTT operations, which require bounded inputs.
 *
 * @param[in] a  16-bit input integer (arbitrary int16_t range).
 * @return       16-bit integer in {-(q-1)/2, ..., (q-1)/2} ≡ a (mod q).
 */
int16_t PQCLEAN_MLKEM768_CLEAN_barrett_reduce(int16_t a) {
    int16_t t;
    /* v = round(2^26 / q): the Barrett magic constant for q = 3329. */
    const int16_t v = ((1 << 26) + KYBER_Q / 2) / KYBER_Q;

    /* t = round(a / q) via the Barrett approximation. */
    t  = ((int32_t)v * a + (1 << 25)) >> 26;
    t *= KYBER_Q;
    return a - t;
}
