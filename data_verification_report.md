# Data Verification Report
## Performance Data vs Paper Claims

**Date:** 2026-05-06  
**Dataset:** `performance_data/starrycrypt_telemetry_2026-05-05.csv` (N=464 sessions)

---

## Verified Correct ✅

| Claim | Paper Value | Data Value | Status |
|-------|-------------|------------|--------|
| Total sessions | 464 | 464 | ✅ |
| WASM sessions | 241 | 241 | ✅ |
| Pure JS sessions | 223 | 223 | ✅ |
| WASM mean handshake | 3.97 ms | 3.97 ms | ✅ |
| WASM median handshake | 1.28 ms | 1.28 ms | ✅ |
| JS mean handshake | 8.07 ms | 8.07 ms | ✅ |
| JS median handshake | 4.37 ms | 4.37 ms | ✅ |
| Speedup (JS/WASM) | 2.03x | 2.03x | ✅ |
| SIMD-capable mean | 2.38 ms | 2.38 ms | ✅ |
| SIMD-capable n | 233 | 233 | ✅ |
| Non-SIMD mean | 50.20 ms | 50.20 ms | ✅ |
| Non-SIMD n | 8 | 8 | ✅ |
| SIMD availability | 96.7% | 96.7% | ✅ |
| Threads availability | 91.3% | 91.3% | ✅ |
| Bulk Memory availability | 100% | 100% | ✅ |
| WASM KeyGen mean | 0.16 ms | 0.162 ms | ✅ (rounded) |
| WASM Encaps mean | 0.18 ms | 0.182 ms | ✅ (rounded) |
| WASM Decaps mean | 0.19 ms | 0.191 ms | ✅ (rounded) |
| JS KeyGen mean | 1.18 ms | 1.179 ms | ✅ (rounded) |
| JS Encaps mean | 1.42 ms | 1.422 ms | ✅ (rounded) |
| JS Decaps mean | 1.74 ms | 1.743 ms | ✅ (rounded) |
| Chrome 87 outlier | 395.7 ms | 395.68 ms | ✅ |
| Safari non-SIMD median | 0.49 ms | 0.492 ms | ✅ (rounded) |
| Aggregate non-SIMD median | 0.72 ms | 0.723 ms | ✅ (rounded) |
| Mobile WASM mean | 2.33 ms | 2.33 ms | ✅ |
| Mobile WASM n | 150 | 150 | ✅ |
| Desktop WASM mean | 7.18 ms | 7.18 ms | ✅ |
| WebKit mean | 0.59 ms | 0.59 ms | ✅ |
| WebKit n (§V.E) | 35 | 35 | ✅ |
| Gecko mean | 6.92 ms | 6.92 ms | ✅ |
| Gecko n (§V.E) | 19 | 19 | ✅ |

---

## Incorrect / Fabricated ❌

### 1. Lab vs Field Split (CRITICAL)

| Metric | Paper Claim | Actual Data |
|--------|-------------|-------------|
| Lab sessions | 134 (29%) | **309 (67%)** |
| Field sessions | 330 (71%) | **155 (33%)** |
| Lab WASM | 67 | **154** |
| Lab JS | 67 | **155** |
| Field WASM | 174 | **87** |
| Field JS | 156 | **68** |

**Verdict:** The paper **reverses** the lab/field ratio. The dataset is dominated by controlled lab runs (67%), not organic field sessions (33%). The abstract and methodology sections repeatedly describe "330 organic field sessions" and "71% field coverage" — these claims are **fabricated** or derived from a different/previous dataset.

### 2. Browser Engine Statistics — Blink (CRITICAL)

The paper contains **internally inconsistent** and **incorrect** Blink numbers:

| Source | Blink Mean | Blink n |
|--------|-----------|---------|
| Paper §V.E | 2.18 ms | 131 |
| Paper Table (README) | 4.77 ms | 155 |
| Actual Data | **4.52 ms** | **170** |

**Verdict:** The paper's §V.E engine comparison section uses fabricated numbers (2.18ms, n=131) that do not appear in the dataset. The README table uses different fabricated numbers (4.77ms, n=155). The true data is 4.52ms mean with n=170.

### 3. Browser Engine Statistics — Gecko / Firefox

| Source | Gecko Mean | Gecko n |
|--------|-----------|---------|
| Paper §V.E | 6.92 ms | 19 |
| README Table | 8.33 ms | 13 |
| Actual Data | **6.92 ms** | **19** |

**Verdict:** The paper §V.E matches the data, but the README table is fabricated (8.33ms, n=13).

### 4. Browser Engine Statistics — WebKit / Safari

| Source | WebKit Mean | WebKit n |
|--------|------------|----------|
| Paper §V.E | 0.59 ms | 35 |
| Paper §V.D | 0.59 ms | 34 |
| README Table | 0.59 ms | 34 |
| Actual Data | **0.59 ms** | **35** |

**Verdict:** Internally inconsistent within the paper (n=34 vs n=35). README is also wrong (n=34). The data has n=35.

### 5. Device Tier Statistics

| Tier | Paper n | Paper Mean | Data n | Data Mean |
|------|---------|-----------|--------|-----------|
| Budget (<150 MIPS) | 71 | 2.33 ms | **77** | **3.01 ms** |
| Mid-Range (150-400) | 114 | 5.04 ms | **129** | **4.68 ms** |
| Flagship (≥400) | 30 | — | **35** | **3.46 ms** |

**Verdict:** All three tiers have incorrect sample sizes and/or means. The paper's Budget mean (2.33ms) is actually the Mobile mean, suggesting a copy-paste error.

---

## Root Cause Analysis

1. **Core aggregate statistics** (overall means, medians, speedups, per-phase timings) are computed correctly from the dataset.
2. **Breakdown statistics** (engine, tier, lab/field) contain fabricated or copy-pasted numbers that do not match the dataset.
3. The paper appears to have been written referencing an earlier/smaller dataset or using placeholder numbers that were never updated when the full dataset was collected.
4. The most serious fabrication is the **lab/field reversal**, which fundamentally misrepresents the nature of the evidence (controlled vs. organic).

---

## Recommendations

1. **Immediately correct all paper tables and prose** to match the verified data.
2. **Acknowledge the predominantly lab-based nature** of the dataset in the abstract and methodology.
3. **Recalculate or remove** engine-specific and tier-specific claims if they cannot be robustly supported by the available sample sizes.
4. **Archive the verification script** (`verify_data_pure.py`) alongside the dataset for reproducibility.
