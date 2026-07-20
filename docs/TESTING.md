# Testing Guide — StarryCrypt-PQC

This document describes every test, verification, and validation procedure
available in the repository and explains what each one checks, how to run it,
and how to interpret its output.

---

## Table of Contents

1. [Test Philosophy](#1-test-philosophy)
2. [WASM Build Verification](#2-wasm-build-verification)
3. [Browser Self-Test (`selfTest`)](#3-browser-self-test-selftest)
4. [Constant-Time Screening (`verifyConstantTimeRejection`)](#4-constant-time-screening)
5. [Statistical Data Verification](#5-statistical-data-verification)
6. [Formal Statistical Tests](#6-formal-statistical-tests)
7. [Known-Answer Test (KAT) Vectors](#7-known-answer-test-kat-vectors)
8. [Paper Figure Reproduction](#8-paper-figure-reproduction)
9. [Interpreting Test Outputs](#9-interpreting-test-outputs)
10. [Limitations](#10-limitations)

---

## 1. Test Philosophy

This project is a research artifact. Its testing strategy is organized around
three distinct concerns:

1. **Correctness** — Does the ML-KEM-768 implementation produce the expected
   key sizes, ciphertext sizes, and shared-secret agreement between
   encapsulator and decapsulator?

2. **Timing safety (developmental screening)** — Does the Fujisaki-Okamoto
   implicit rejection path exhibit a statistically significant timing
   difference compared to the valid ciphertext path? (Note: this is a
   developmental screening tool, not a formal TVLA evaluation.)

3. **Statistical reproducibility** — Do the reported numerical claims in the
   paper follow from the raw telemetry data via transparent, verifiable
   arithmetic?

---

## 2. WASM Build Verification

```bash
# Build the WASM module from source
make all

# Expected output:
#   WASM build complete: dist/mlkem768.js + dist/mlkem768.wasm
```

Verify the output files exist and are non-empty:

```bash
ls -lh dist/mlkem768.js dist/mlkem768.wasm
```

Expected sizes (approximate — vary with Emscripten version):
- `dist/mlkem768.js`  — ~180–220 KB (Emscripten glue)
- `dist/mlkem768.wasm` — ~60–90 KB (compiled ML-KEM-768)

If the build fails with "not found: emcc", ensure the Emscripten SDK is
activated:
```bash
source /path/to/emsdk/emsdk_env.sh
```

---

## 3. Browser Self-Test (`selfTest`)

**Location:** `src/js/mlkem768-wrapper.js` — `selfTest()` and `selfTestPureJS()`  
**Entry point:** Open `benchmark/index.html` in a browser, open DevTools Console,
and run:

```javascript
// WASM implementation
import('./dist/mlkem768-wrapper.js').then(m => m.selfTest().then(console.log));

// Pure-JS implementation
import('./src/js/purejs-wrapper.js').then(m => m.selfTest().then(console.log));
```

Or use the "Run Self-Test" button on the benchmark page.

**What it checks:**

| Check | Expected |
|-------|----------|
| Public key size | 1184 bytes |
| Secret key size | 2400 bytes |
| Ciphertext size | 1088 bytes |
| Shared secret size | 32 bytes |
| Shared secret agreement (Alice == Bob) | `true` |
| AES-GCM round-trip | plaintext == decrypted plaintext |
| X25519 key agreement | Both sides derive equal shared secret |

**Passing output:**
```json
{
  "passed": true,
  "checks": {
    "pkSize": true,
    "skSize": true,
    "ctSize": true,
    "ssSize": true,
    "ssMatch": true,
    "aesRoundTrip": true,
    "x25519Match": true
  }
}
```

A `false` value on any check indicates a regression and must be investigated
before submitting a pull request.

---

## 4. Constant-Time Screening

**Location:** `src/js/mlkem768-wrapper.js` — `verifyConstantTimeRejection()`  
**Entry point:** Browser DevTools Console or benchmark page "Run Timing Test" button.

```javascript
import('./dist/mlkem768-wrapper.js').then(m =>
  m.verifyConstantTimeRejection(200).then(console.log)
);
```

**What it checks:**

Runs 200 decapsulations with valid ciphertexts and 200 decapsulations with
randomly corrupted ciphertexts. Computes a Welch t-statistic on the two
timing distributions.

| t-statistic | Interpretation |
|-------------|----------------|
| `|t| < 2.0` | No statistically significant timing difference — PASS |
| `2.0 <= |t| < 4.5` | Marginal; investigate browser/OS before reporting |
| `|t| >= 4.5` | Significant timing difference detected — FAIL; report as issue |

**Expected passing output:**
```json
{
  "passed": true,
  "tStatistic": 0.847,
  "message": "No significant timing difference detected (|t| = 0.85 < 4.5)"
}
```

**Important caveat:** This test uses browser `performance.now()` which has
µs-level precision on most browsers. It is a screening tool only — a passing
result does not guarantee formal constant-time behaviour. Do not deploy this
implementation in a production context based solely on this test.

---

## 5. Statistical Data Verification

**Script:** `scripts/verify_data.py`  
**Dependencies:** Python 3.8+ standard library only (no external packages)

```bash
python3 scripts/verify_data.py
```

**What it checks:**

Recomputes every numeric claim in the paper and `verification_report.md` from
the raw telemetry CSV. Outputs:

- Total sessions and implementation split (WASM vs. Pure-JS)
- Overall handshake latency statistics (mean, median, std, P95)
- WASM vs. Pure-JS speedup ratio
- SIMD vs. non-SIMD WASM subgroup statistics
- Per-phase timing (KeyGen, Encaps, Decaps) for both implementations
- Browser engine (Blink, WebKit, Gecko) breakdown
- Mobile vs. Desktop comparison
- Field vs. Lab session classification
- WASM feature availability (SIMD, Threads, Bulk Memory)
- Chrome 87 outlier identification

**Expected output (key values):**
```
WASM: n=240, mean=2.34ms, median=1.28ms
JS:   n=223, mean=8.07ms, median=4.37ms
Speedup: 3.45x
```

If values diverge from `verification_report.md`, the telemetry CSV or the
exclusion policy has changed — investigate before reporting.

---

## 6. Formal Statistical Tests

**Script:** `analysis/statistical_tests.py`  
**Dependencies:** `numpy >= 1.21`, `scipy >= 1.7`

```bash
python3 analysis/statistical_tests.py
```

**What it computes:**

| Test | Parameters | Expected Result |
|------|-----------|-----------------|
| Welch's t-test (full dataset) | WASM vs. JS `total_handshake_mean` | p < 0.0001 |
| Welch's t-test (outlier excluded) | WASM vs. JS, Chrome 87 removed | p < 0.0001 |
| Cohen's d (full) | Pooled std formulation | d > 0.8 (large effect) |
| Cohen's d (outlier excluded) | Pooled std | d > 0.8 |
| 95% CI for WASM mean | Student t, df = n-1 | Narrow interval |
| 95% CI for JS mean | Student t, df = n-1 | Wider interval |

**Post-hoc power analysis:**
```bash
python3 analysis/statistical_power_analysis.py
```
Expected: post-hoc power > 0.99 for the observed effect size and sample sizes.

---

## 7. Known-Answer Test (KAT) Vectors

ML-KEM-768 KAT vectors are defined in NIST FIPS 203, Annex A. Verification
against these vectors confirms that the WASM implementation matches the
reference C implementation byte-for-byte.

**Current status:** KAT vector testing is on the roadmap (see CONTRIBUTING.md
§7). To run an informal correctness check, `selfTest()` confirms shared-secret
agreement but does not compare against fixed test vectors.

**To contribute KAT tests:**
1. Obtain the KAT vectors from the [NIST PQC Round 3 KAT files](https://csrc.nist.gov/Projects/post-quantum-cryptography).
2. Implement a JavaScript test harness that calls `mlkemKeyGen`, `mlkemEncaps`,
   and `mlkemDecaps` with the KAT seed and compares the output to the expected
   values.
3. See CONTRIBUTING.md §7 for the contribution workflow.

---

## 8. Paper Figure Reproduction

```bash
# Activate the Python virtual environment
source .venv/bin/activate

# Reproduce all 8 publication figures
make figures
```

**Output:** `analysis/figures/fig{1..8}_*.pdf` and `.png`.

Each figure should visually match the version submitted to IACR ePrint. Minor
rendering differences (font substitution, anti-aliasing) are acceptable; data
differences are not.

To verify a specific figure's underlying data, trace the corresponding `fig*`
function in `analysis/generate_figures.py` — each function is documented with
the data it uses and the expected visual structure.

---

## 9. Interpreting Test Outputs

| Output | Meaning |
|--------|---------|
| `selfTest.passed == true` | All correctness checks passed |
| `|t| < 2.0` in timing test | Timing screening passes |
| Verify script values match report | Dataset and analysis pipeline consistent |
| `p < 0.05` in Welch t-test | WASM vs. JS difference is statistically significant |
| `d > 0.8` Cohen's d | Large practical effect size |
| Figures visually match submission | Figure generation pipeline consistent |

---

## 10. Limitations

- **No automated CI:** Tests are run manually. Browser tests require a
  human-in-the-loop to open the benchmark page and check the console.
- **KAT vectors not yet implemented:** The implementation is verified by
  cross-checking against the PQClean reference and by `selfTest()` shared-
  secret agreement, not by NIST KAT byte-by-byte comparison.
- **Timing test precision:** `performance.now()` resolution varies by browser
  (`0.1 µs` on Chrome, `1 ms` on Firefox with cross-origin isolation disabled).
  On Firefox without cross-origin isolation, the timing test may have reduced
  discriminating power.
- **No thread-safety testing:** SharedArrayBuffer-based parallel benchmarks
  are a planned feature; thread-safety of the WASM module has not been tested.
