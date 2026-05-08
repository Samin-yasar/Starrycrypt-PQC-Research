# Paper Claims Verification Report

## Summary
All major claims have been verified against the performance data. Two critical statistical errors were identified and corrected:

1. **§V.A Safari non-SIMD median**: Corrected from 0.72ms to 0.49ms (0.72ms is the aggregate non-SIMD median, not Safari-only)
2. **§V.C "median inflated by outlier"**: Removed statistically incorrect claim. Medians are robust to outliers by definition. The Chrome 87 outlier inflates the *mean*, not the median.

## Verified Claims

### 1. Overall WASM vs JS Performance
| Claim | Data | Status |
|-------|------|--------|
| 2.99× speedup | 2.99× (WASM 2.34ms vs JS 6.99ms) | ✓ VERIFIED |
| WASM mean 2.34ms | 2.34ms (n=240) | ✓ VERIFIED |
| WASM median 1.28ms | 1.28ms | ✓ VERIFIED |
| JS mean 6.99ms | 6.99ms (n=222) | ✓ VERIFIED |
| JS median 4.37ms | 4.37ms | ✓ VERIFIED |

### 2. SIMD vs Non-SIMD
| Claim | Data | Status |
|-------|------|--------|
| SIMD mean 2.38ms | 2.38ms (n=233) | ✓ VERIFIED |
| Non-SIMD mean 50.20ms | 50.20ms (n=8) | ✓ VERIFIED |
| Chrome 87 outlier 395.7ms | 395.68ms | ✓ VERIFIED |
| Safari non-SIMD median | 0.49ms (was 0.72ms) | ✓ CORRECTED |
| Aggregate non-SIMD median | 0.72ms | ✓ VERIFIED |

### 3. Per-Phase Performance
| Claim | Data | Status |
|-------|------|--------|
| WASM KeyGen 0.16ms | 0.162ms | ✓ VERIFIED |
| WASM Encaps 0.18ms | 0.182ms | ✓ VERIFIED |
| WASM Decaps 0.19ms | 0.191ms | ✓ VERIFIED |
| JS KeyGen 1.18ms | 1.179ms | ✓ VERIFIED |
| JS Encaps 1.42ms | 1.422ms | ✓ VERIFIED |
| JS Decaps 1.74ms | 1.743ms | ✓ VERIFIED |

### 4. WASM Feature Availability
| Claim | Data | Status |
|-------|------|--------|
| SIMD 96.7% | 96.7% | ✓ VERIFIED |
| Threads 91.3% | 91.3% | ✓ VERIFIED |
| Bulk Memory 100% | 100% | ✓ VERIFIED |

### 5. Mobile vs Desktop
| Claim | Data | Status |
|-------|------|--------|
| Mobile 2.33ms | 2.33ms (n=150) | ✓ VERIFIED |
| Desktop 7.18ms | 7.18ms (n=84) | ✓ VERIFIED |

### 6. Dataset Composition
| Claim | Data | Status |
|-------|------|--------|
| Total 462 sessions | 462 | ✓ VERIFIED |
| WASM 240 sessions | 240 | ✓ VERIFIED |
| Pure JS 222 sessions | 222 | ✓ VERIFIED |
| Lab 307 sessions | 307 (153 WASM, 154 JS) | ✓ VERIFIED |
| Field 155 sessions | 155 (87 WASM, 68 JS) | ✓ VERIFIED |

## Citations Verification

| Citation | Context | Status |
|----------|---------|--------|
| Shor 1994 | Quantum algorithms threat | ✓ Appropriate |
| NIST FIPS 203 | ML-KEM standardization | ✓ Core reference |
| Haas et al. 2017 | WebAssembly overview | ✓ Appropriate |
| Stebila et al. 2026 | Hybrid key exchange draft | ✓ Appropriate |
| Reparaz et al. 2017 | Welch's t-test methodology | ✓ Appropriate |
| Almeida et al. 2016 | Constant-time verification | ✓ Appropriate |
| Google V8 Benchmarking | JIT warm-up guidance | ✓ Appropriate |
| Bindel et al. 2017 | Hybrid key exchange security | ✓ Appropriate |

## Logic and Argumentation Strength

### Strong Claims (well-supported by data):
1. **WASM delivers 2.99× speedup over pure JS** - Directly supported by mean comparison (outliers excluded)
2. **Modern SIMD browsers achieve ~2.4ms mean** - Direct measurement
3. **Browser vintage matters more than SIMD** - Safari non-SIMD (0.49ms) comparable to SIMD browsers
4. **Chrome 87 shows anomalous latency** - Clear outliers at 395.7ms (WASM) and 247.4ms (JS)

### Transparent Disclosures (properly qualified):
1. **Chrome 87 outlier identified** - Explicitly noted as browser-era issue
2. **Non-SIMD variance explained** - Safari vs Chrome distinction clear
3. **TVLA limitations stated** - N=100 insufficient for security guarantee
4. **Geographic bias acknowledged** - South Asia concentration noted

## Review-Driven Revisions (Implemented)

### 1. Abstract Updated
**Change:** Clarified that "performance is primarily determined by browser runtime vintage rather than SIMD instruction availability."
**Status:** ✓ IMPLEMENTED

### 2. Section 5.3 (WASM Feature Availability)
**Changes:**
- Added explicit sample size breakdown: Safari ($n=7$), Chrome ($n=1$)
- Changed "likely a browser-era WASM implementation issue" to "potentially a browser-era WASM implementation issue... though with $n=1$ this conclusion is necessarily speculative"
- Added note: "n=1 for Chrome non-SIMD"
**Status:** ✓ IMPLEMENTED

### 3. Section 5.6 (Compute-Latency Scaling)
**Changes:**
- Added: "With $n=1$ for Chrome non-SIMD, any attribution to browser-era implementation is speculative"
- Clarified: "browser vintage, not SIMD instruction availability, is the dominant performance factor"
**Status:** ✓ IMPLEMENTED

### 4. Conclusion
**Changes:**
- Added: "With only $n=1$ for Chrome non-SIMD, any causal attribution to browser-era implementation is necessarily speculative"
- Emphasized: "modern non-SIMD browsers (Safari $n=7$, median $0.49$ ms) achieve performance comparable to SIMD-capable browsers"
**Status:** ✓ IMPLEMENTED

### 5. Limitations Section
**Changes:**
- Added explicit note: "non-SIMD browser samples are small: Safari ($n=7$), Chrome ($n=1$), totaling $n=8$---insufficient for robust vendor-specific conclusions"
- Added: "Any attribution of the Chrome~87 outlier to browser-era implementation is necessarily speculative given $n=1$"
**Status:** ✓ IMPLEMENTED

### 6. Figure 5 Caption (Future)
**Recommendation:** The figure caption currently states: "Seven Safari non-SIMD sessions achieved median $0.49$~ms; one legacy Chrome~87 outlier at $395.7$~ms inflates the aggregate non-SIMD mean to $50.2$~ms."
**Future work:** Consider adding a visualization that separates Safari non-SIMD from Chrome non-SIMD, or explicitly label the figure: "Non-SIMD performance varies dramatically by browser vendor (Safari $n=7$ vs Chrome $n=1$)."
**Status:** PENDING (requires figure regeneration)

## Files Updated

### paper.tex
- Section 5.1: Updated WASM vs JS statistics (N=462, 2.99× speedup)
- Table 1: Updated Summary of Key Performance Results
- Section 5.3: Transparent disclosure about non-SIMD variance
- Section 5.4: Browser engine statistics with outlier transparency
- Section 5.6: Corrected Safari non-SIMD median (0.49ms)
- Conclusion: Updated all statistics to N=462 policy

### index.html
- Hero stats: 2.99× speedup, 2.34ms WASM mean
- Discovery section: Transparent legacy browser analysis
- Insight cards: Corrected statistics (N=462)
- Chart data: [1.82, 6.99, 50.20] (Chromium SIMD, Pure JS, Non-SIMD)
- Implementation cards: Updated means and per-phase data

## Conclusion
All paper claims are now accurately backed by the performance data with full transparency about outliers and variance.

## Statistical Corrections (2026-05-06)

### Issue 1: Internal Numerical Contradiction on Safari non-SIMD Median

**Problem:** The same metric was reported as two different values:
- Abstract: "seven Safari non-SIMD sessions achieved median 0.49 ms" ✓
- §V.A: "seven Safari sessions on iOS/iPadOS 15 achieved median 0.72 ms" ✗ (incorrect)
- §V.C: "Safari (n=7) on iOS/iPadOS 15 achieved excellent performance (median 0.49 ms)" ✓
- §VII: "seven Safari non-SIMD sessions on iOS/iPadOS 15 achieved median 0.49 ms" ✓

**Root Cause:** The 0.72 ms figure in §V.A was the aggregate non-SIMD median (all 8 sessions), not the Safari-only median. This was a substitution error.

**Fix:** Corrected §V.A to state Safari non-SIMD median as 0.49 ms.

### Issue 2: Statistically Incorrect Claim About Median

**Problem:** §V.C stated: "The aggregate non-SIMD median was 0.72 ms (inflated by the Chrome 87 outlier)."

**Why This Is Wrong:** Medians are explicitly robust to outliers — this is their defining property. With 8 values:
- Sorted: [0.412, 0.453, 0.458, 0.492, 0.954, 1.172, 1.982, 395.683]
- Median = (4th + 5th) / 2 = (0.492 + 0.954) / 2 = 0.723 ms
- Mean = (sum of all 8) / 8 = 50.2 ms ← correctly "inflated" by outlier

The outlier (395.7 ms) is the 8th value and does not affect the median calculation at all.

**Fix:** Rewrote to correctly state that the outlier inflates the *mean*, while the median remains robust.

### Data Verification

Non-SIMD WASM sessions (n=8):

| Browser | OS | Version | Latency (ms) |
|---------|-----|---------|--------------|
| Safari | iPadOS | 15.5 | 0.453 |
| Safari | iPadOS | 15.5 | 0.458 |
| Safari | iPadOS | 15.5 | 0.492 |
| Safari | iOS | 15.4 | 0.412 |
| Safari | macOS | 15.6.1 | 1.172 |
| Safari | macOS | 15.6.1 | 1.982 |
| Safari | macOS | 16.1 | 0.954 |
| Chrome | macOS | 87 | 395.683 |

**Calculated Values:**
- Safari non-SIMD (n=7): median = 0.492 ms ✓
- Aggregate non-SIMD (n=8): median = 0.723 ms ✓
- Aggregate non-SIMD (n=8): mean = 50.2 ms ✓
