/**
 * @file verify.c
 * @brief Constant-time comparison and conditional copy primitives.
 *
 * This file provides the timing-safe byte-array comparison and conditional
 * assignment routines required by the Fujisaki-Okamoto decapsulation check
 * in kem.c. Every function executes in data-independent time — execution
 * time must not vary with the values of the input bytes.
 *
 * SECURITY RATIONALE
 * ------------------
 * A straightforward memcmp() is NOT safe for the re-encryption check in
 * decapsulation: a short-circuit comparison would leak the position of the
 * first differing byte, giving an attacker a padding-oracle-style side
 * channel. The functions below use bitwise reduction (OR of all XOR
 * differences) to produce a result without any data-dependent control flow.
 *
 * Similarly, the conditional copy (cmov) must not branch on the condition
 * bit b. A naive "if (b) memcpy" would be correctly compiled only if the
 * compiler has no opportunity to short-circuit — which is generally not
 * guaranteed. The PQCLEAN_PREVENT_BRANCH_HACK macro (compat.h) inserts an
 * opaque ASM or volatile fence to prevent the compiler from transforming
 * the mask operation back into a branch.
 *
 * COMPILER ASSUMPTIONS
 * --------------------
 * The following properties are required for correctness but are NOT
 * guaranteed by the C standard; they hold on all Emscripten/WASM targets
 * and on standard hosted x86/ARM64 platforms:
 *   - int16_t and uint8_t use two's complement representation.
 *   - Right-shifting a negative int64 arithmetic-shifts (sign-extends)
 *     rather than truncating (used in verify() to map a non-zero r to 1).
 *
 * Reference: FIPS 203 §7.3 (implicit rejection); PQCLEAN verify.c.
 */

#include "compat.h"
#include "verify.h"
#include <stddef.h>
#include <stdint.h>

/**
 * PQCLEAN_MLKEM768_CLEAN_verify — constant-time byte-array comparison.
 *
 * Compares two byte arrays a and b of length len in constant time by
 * computing the bitwise OR of all pairwise XOR differences:
 *
 *   r = a[0] ^ b[0] | a[1] ^ b[1] | ... | a[len-1] ^ b[len-1]
 *
 * r == 0 iff all bytes are equal. The return value is derived via an
 * arithmetic right-shift of (-r cast to int64), which propagates the sign
 * bit: if r != 0 then (-r) has bit 63 set, and >> 63 gives 1.
 *
 * This function processes all len bytes regardless of whether a mismatch
 * is found early; there is no early exit.
 *
 * @param[in] a    First byte array.
 * @param[in] b    Second byte array.
 * @param[in] len  Number of bytes to compare.
 * @return 0 if a[0..len-1] == b[0..len-1]; 1 otherwise.
 */
int PQCLEAN_MLKEM768_CLEAN_verify(const uint8_t *a, const uint8_t *b, size_t len) {
    size_t i;
    uint8_t r = 0;

    for (i = 0; i < len; i++) {
        r |= a[i] ^ b[i];
    }

    /* Arithmetic right-shift: maps any non-zero r to 1, zero r to 0. */
    return (-(uint64_t)r) >> 63;
}

/**
 * PQCLEAN_MLKEM768_CLEAN_cmov — constant-time conditional byte-array copy.
 *
 * If b == 1: copies x[0..len-1] into r[0..len-1].
 * If b == 0: r is unchanged.
 *
 * Implementation uses bitwise masking:
 *   mask = -(uint8_t)b    (b=0 → mask=0x00; b=1 → mask=0xFF in two's complement)
 *   r[i] ^= mask & (r[i] ^ x[i])
 *
 * When mask == 0xFF: r[i] ^= (r[i] ^ x[i]) = x[i]    (copy x)
 * When mask == 0x00: r[i] ^= 0              = r[i]    (unchanged)
 *
 * The PQCLEAN_PREVENT_BRANCH_HACK fence (compat.h) prevents the compiler
 * from proving that b is a constant and transforming this into a branch.
 *
 * PRECONDITION: b MUST be in {0, 1}. Passing any other value produces
 * undefined behavior due to the two's complement negation assumption.
 *
 * @param[in,out] r    Output buffer (modified in-place when b == 1).
 * @param[in]     x    Source buffer.
 * @param[in]     len  Number of bytes to (conditionally) copy.
 * @param[in]     b    Condition bit; MUST be 0 or 1.
 */
void PQCLEAN_MLKEM768_CLEAN_cmov(uint8_t *r, const uint8_t *x, size_t len, uint8_t b) {
    size_t i;

    /* Opaque fence: prevents compiler from proving b is constant. */
    PQCLEAN_PREVENT_BRANCH_HACK(b);

    /* b=0 → mask=0x00 (no copy); b=1 → mask=0xFF (full copy). */
    b = -b;
    for (i = 0; i < len; i++) {
        r[i] ^= b & (r[i] ^ x[i]);
    }
}

/**
 * PQCLEAN_MLKEM768_CLEAN_cmov_int16 — constant-time conditional int16 copy.
 *
 * If b == 1: writes v into *r.
 * If b == 0: *r is unchanged.
 *
 * Applies the same bitwise masking technique as cmov() but to a single
 * int16_t value. Used by the NTT and polynomial reduction layers.
 *
 * PRECONDITION: b MUST be in {0, 1}.
 *
 * @param[in,out] r  Pointer to the int16_t to (conditionally) overwrite.
 * @param[in]     v  The int16_t value to copy if b == 1.
 * @param[in]     b  Condition bit; MUST be 0 or 1.
 */
void PQCLEAN_MLKEM768_CLEAN_cmov_int16(int16_t *r, int16_t v, uint16_t b) {
    b = -b;
    *r ^= b & ((*r) ^ v);
}
