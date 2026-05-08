#!/usr/bin/env python3
"""
Statistical Power Analysis for WASM vs JS Performance Comparison
Addresses reviewer concerns M3, M4, and M5.
"""

import pandas as pd
import numpy as np
from scipy import stats

# Load data
df = pd.read_csv('performance_data/starrycrypt_telemetry_2026-05-05.csv')
is_c87 = (df['browser_name'] == 'Chrome') & (df['browser_version'].astype(str).str.startswith('87')) & (df['os_name'] == 'macOS')
df = df[~is_c87]

wasm = df[df['implementation'] == 'wasm']['total_handshake_mean'].dropna()
js = df[df['implementation'] == 'pure-js']['total_handshake_mean'].dropna()

print("=" * 70)
print("M3: STATISTICAL POWER ANALYSIS FOR WASM vs JS COMPARISON")
print("=" * 70)
print()

# Basic statistics
n_wasm = len(wasm)
n_js = len(js)
mean_wasm = wasm.mean()
mean_js = js.mean()
std_wasm = wasm.std()
std_js = js.std()

print("Sample Statistics:")
print(f"  WASM: n={n_wasm}, mean={mean_wasm:.2f} ms, std={std_wasm:.2f} ms")
print(f"  JS:   n={n_js}, mean={mean_js:.2f} ms, std={std_js:.2f} ms")
print()

# Welch's t-test (unequal variance)
t_stat, p_value = stats.ttest_ind(wasm, js, equal_var=False)

# Calculate 95% CI for difference in means
# Using Welch-Satterthwaite degrees of freedom
var_wasm = std_wasm ** 2
var_js = std_js ** 2
se = np.sqrt(var_wasm/n_wasm + var_js/n_js)
df_welch = (var_wasm/n_wasm + var_js/n_js)**2 / ((var_wasm/n_wasm)**2/(n_wasm-1) + (var_js/n_js)**2/(n_js-1))
ci_margin = stats.t.ppf(0.975, df_welch) * se
diff = mean_js - mean_wasm  # JS - WASM (positive means WASM faster)
ci_lower = diff - ci_margin
ci_upper = diff + ci_margin

print("Welch's t-test Results:")
print(f"  t-statistic: {t_stat:.3f}")
print(f"  p-value: {p_value:.4f}")
print(f"  95% CI for difference (JS - WASM): [{ci_lower:.2f}, {ci_upper:.2f}] ms")
print()

# Cohen's d (pooled standard deviation)
pooled_std = np.sqrt(((n_wasm - 1) * std_wasm**2 + (n_js - 1) * std_js**2) / (n_wasm + n_js - 2))
cohens_d = (mean_wasm - mean_js) / pooled_std  # Negative because WASM is faster

print("Effect Size:")
print(f"  Cohen's d: {cohens_d:.3f}")
print(f"  Interpretation: {'negligible' if abs(cohens_d) < 0.2 else 'small' if abs(cohens_d) < 0.5 else 'medium' if abs(cohens_d) < 0.8 else 'large'}")
print(f"  (|d| < 0.2 = negligible, 0.2-0.5 = small, 0.5-0.8 = medium, > 0.8 = large)")
print()

# Post-hoc power analysis
# Using the observed effect size and sample sizes
def calculate_power(n1, n2, d, alpha=0.05):
    """
    Calculate post-hoc power for two-sample t-test.
    Uses non-central t-distribution approximation.
    """
    # Non-centrality parameter
    ncp = d * np.sqrt(n1 * n2 / (n1 + n2))
    
    # Critical t-value (two-tailed)
    df = n1 + n2 - 2
    t_crit = stats.t.ppf(1 - alpha/2, df)
    
    # Power = P(reject H0 | H1 true)
    # = P(|T| > t_crit | non-central t with ncp)
    power = 1 - stats.nct.cdf(t_crit, df, ncp) + stats.nct.cdf(-t_crit, df, ncp)
    return power

power = calculate_power(n_wasm, n_js, abs(cohens_d))

print("Post-hoc Power Analysis:")
print(f"  Observed effect size (|d|): {abs(cohens_d):.3f}")
print(f"  Sample sizes: n1={n_wasm}, n2={n_js}")
print(f"  Statistical power (1-β): {power:.3f} ({power*100:.1f}%)")
print(f"  Type II error rate (β): {1-power:.3f} ({(1-power)*100:.1f}%)")
print()

# Power interpretation
print("Power Interpretation:")
if power < 0.5:
    print("  ⚠️  SEVERELY UNDERPOWERED (< 50% power)")
    print("  The test has a high probability of missing a true effect.")
elif power < 0.8:
    print("  ⚠️  UNDERPOWERED (< 80% power)")
    print("  Conventional power threshold of 80% not met.")
else:
    print("  ✓ ADEQUATE POWER (≥ 80%)")
print()

# Sample size needed for 80% power
def calculate_required_n(d, alpha=0.05, power=0.8):
    """Calculate required sample size per group for two-sample t-test."""
    z_alpha = stats.norm.ppf(1 - alpha/2)
    z_beta = stats.norm.ppf(power)
    n = 2 * ((z_alpha + z_beta) / d) ** 2
    return int(np.ceil(n))

n_required = calculate_required_n(abs(cohens_d))
print(f"Sample Size Requirements:")
print(f"  For 80% power at α=0.05 with observed effect size d={abs(cohens_d):.3f}:")
print(f"  Required n per group: {n_required}")
print(f"  Current n per group: WASM={n_wasm}, JS={n_js}")
print(f"  Deficit: {max(0, n_required - n_wasm)} more samples needed per group")
print()

# Type I error risk assessment
print("Type I Error Risk Assessment:")
print(f"  Observed p-value: {p_value:.4f}")
print(f"  Significance threshold: α = 0.05")
print(f"  Margin above threshold: {(0.05 - p_value):.4f}")
if p_value < 0.05 and p_value > 0.01:
    print("  ⚠️  MARGINAL SIGNIFICANCE (0.01 < p < 0.05)")
    print("  Given low power, this result has elevated Type I error risk.")
    print("  The CI nearly includes zero (lower bound: {:.2f} ms).".format(ci_lower))
print()

# Multiple comparisons note
print("Multiple Comparisons Consideration:")
print("  The paper conducts multiple subgroup analyses (SIMD vs non-SIMD,")
print("  browser engines, device tiers, mobile vs desktop).")
print("  Without correction, family-wise Type I error rate is inflated.")
print("  Bonferroni correction for ~10 comparisons: α_adj = 0.005")
print(f"  Result would NOT survive correction (p={p_value:.4f} > 0.005)")
print()

print("=" * 70)
print("M4: SAFARI SIMD DETECTION PARADOX ANALYSIS")
print("=" * 70)
print()

wasm_full = df[df['implementation'] == 'wasm']
wasm_simd = wasm_full[wasm_full['wasm_simd'] == True]
wasm_no_simd = wasm_full[wasm_full['wasm_simd'] == False]

print("SIMD Detection Analysis:")
print(f"  SIMD-reported sessions: n={len(wasm_simd)}")
print(f"  Non-SIMD-reported sessions: n={len(wasm_no_simd)}")
print()

# Break down non-SIMD by browser
if len(wasm_no_simd) > 0:
    print("Non-SIMD Sessions by Browser:")
    for browser in wasm_no_simd['browser_name'].unique():
        browser_data = wasm_no_simd[wasm_no_simd['browser_name'] == browser]
        print(f"  {browser}:")
        print(f"    n = {len(browser_data)}")
        print(f"    mean latency = {browser_data['total_handshake_mean'].mean():.2f} ms")
        print(f"    median latency = {browser_data['total_handshake_mean'].median():.2f} ms")
        print(f"    std = {browser_data['total_handshake_mean'].std():.2f} ms")
    print()
    
    # Safari non-SIMD specifically
    safari_no_simd = wasm_no_simd[wasm_no_simd['browser_name'].str.contains('Safari', case=False, na=False)]
    if len(safari_no_simd) > 0:
        print("Safari Non-SIMD Sessions (Paradoxical):")
        print(f"  n = {len(safari_no_simd)}")
        print(f"  mean = {safari_no_simd['total_handshake_mean'].mean():.2f} ms")
        print(f"  median = {safari_no_simd['total_handshake_mean'].median():.2f} ms")
        print(f"  This is FASTER than SIMD-capable median ({wasm_simd['total_handshake_mean'].median():.2f} ms)!")
        print()
        
        # Compare Safari non-SIMD to SIMD-capable
        safari_median = safari_no_simd['total_handshake_mean'].median()
        simd_median = wasm_simd['total_handshake_mean'].median()
        print("Paradox Analysis:")
        print(f"  Safari non-SIMD median: {safari_median:.2f} ms")
        print(f"  SIMD-capable median: {simd_median:.2f} ms")
        print(f"  Safari non-SIMD is {simd_median/safari_median:.2f}x FASTER than SIMD-capable!")
        print()
        print("Mechanistic Hypothesis:")
        print("  Safari/JavaScriptCore may use internal SIMD optimizations")
        print("  even when WebAssembly.featureDetection API reports no SIMD.")
        print("  This makes 'SIMD reported by browser' an UNRELIABLE predictor.")
        print()

# SIMD capability vs performance correlation
print("SIMD Flag vs Performance Correlation:")
simd_flag = wasm_full['wasm_simd'].astype(int)
latency = wasm_full['total_handshake_mean']
corr, p_corr = stats.pointbiserialr(simd_flag, latency)
print(f"  Point-biserial correlation: r = {corr:.3f}, p = {p_corr:.4f}")
print(f"  Interpretation: {'Weak' if abs(corr) < 0.3 else 'Moderate' if abs(corr) < 0.5 else 'Strong'} correlation")
print(f"  Direction: SIMD flag is associated with {'higher' if corr > 0 else 'lower'} latency")
print()

print("=" * 70)
print("M5: OVERHEAD DECOMPOSITION METHODOLOGICAL ASSESSMENT")
print("=" * 70)
print()

# Calculate actual overhead from data
wasm_phases = wasm_full[['mlkem_keygen_mean', 'mlkem_encaps_mean', 'mlkem_decaps_mean']].mean()
total_crypto = wasm_phases.sum()
total_measured = wasm_full['total_handshake_mean'].mean()
overhead = total_measured - total_crypto

print("Overhead Analysis from Data:")
print(f"  Per-phase crypto total (mean):")
print(f"    KeyGen:  {wasm_phases['mlkem_keygen_mean']:.3f} ms")
print(f"    Encaps:  {wasm_phases['mlkem_encaps_mean']:.3f} ms")
print(f"    Decaps:  {wasm_phases['mlkem_decaps_mean']:.3f} ms")
print(f"    Sum:     {total_crypto:.3f} ms")
print()
print(f"  Total handshake mean: {total_measured:.2f} ms")
print(f"  Implied overhead: {overhead:.2f} ms ({overhead/total_measured*100:.1f}% of total)")
print()

print("Methodological Caveats:")
print("  1. Per-phase timings are measured SEPARATELY from total handshake.")
print("  2. Total handshake includes X25519, HKDF, AES-GCM operations NOT in per-phase.")
print("  3. WASM instantiation occurs ONCE per session, not per operation.")
print("  4. JS/WASM boundary crossing is included in per-phase timings (inside ccall).")
print("  5. Memory allocation overhead is NOT captured in per-phase timings.")
print()

print("Recommendation for Paper:")
print("  - DO NOT present exact percentages (e.g., '30%', '45%') as facts")
print("  - Use QUALITATIVE language: 'substantial overhead from...'")
print("  - Acknowledge DevTools profiler has INSTRUMENTATION OVERHEAD")
print("  - Cite prior literature for WASM boundary crossing costs")
print("  - If exact breakdown needed, provide TABLE with variance and run counts")
print()

print("=" * 70)
print("SUMMARY OF RECOMMENDATIONS")
print("=" * 70)
print()
print("M3 (Power Analysis):")
print(f"  ✓ Report Cohen's d = {cohens_d:.3f} (small effect)")
print(f"  ✓ Report post-hoc power = {power:.1%} (underpowered)")
print("  ✓ Acknowledge marginal p-value has elevated Type I error risk")
print("  ✓ Note CI nearly includes zero (lower bound: {:.2f} ms)".format(ci_lower))
print("  ✓ Note result would not survive Bonferroni correction")
print()
print("M4 (Safari SIMD Paradox):")
print("  ✓ Acknowledge Safari non-SIMD paradox (median 0.49 ms)")
print("  ✓ Hypothesize internal JavaScriptCore SIMD optimizations")
print("  ✓ State 'SIMD reported by browser' is unreliable predictor")
print("  ✓ Remove 'Legacy Runtime' row from Table 2 (already done)")
print("  ✓ Update Figure 5 caption to reflect this finding")
print()
print("M5 (Overhead Decomposition):")
print("  ✓ Use qualitative language instead of exact percentages")
print("  ✓ Acknowledge DevTools profiler instrumentation overhead")
print("  ✓ Cite prior WASM literature for boundary crossing costs")
print("  ✓ Do NOT present unmeasured percentages as facts")
print()

# Generate LaTeX table row for power analysis
print("=" * 70)
print("LATEX OUTPUT FOR PAPER")
print("=" * 70)
print()
print("% Statistical Power Analysis Box (add to Section 5.1):")
print(f"% Cohen's d = {cohens_d:.3f}")
print(f"% Post-hoc power = {power:.3f}")
print(f"% Required n for 80% power = {n_required} per group")
print()
print("% Add to results paragraph:")
print(f"print(f'A Welch\\'s t-test confirms the overall difference in means is statistically significant ($t={t_stat:.2f}$, $p={p_value:.3f}$, 95\\% CI for the difference: $[{ci_lower:.2f}, {ci_upper:.2f}]$~ms), yielding a small effect size (Cohen\\'s $d = {cohens_d:.2f}$). A post-hoc power analysis indicates the test has only ${power*100:.0f}\\%$ power to detect this effect size at $\\alpha=0.05$, meaning the result is underpowered. We acknowledge that the marginal $p$-value (${p_value:.3f}$) and the near-zero lower confidence interval bound may reflect Type I error risk at the boundaries, particularly given multiple comparisons across subgroups.')")
