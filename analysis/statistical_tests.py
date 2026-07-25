#!/usr/bin/env python3
"""
StarryCrypt-PQC — Hypothesis Testing & Statistical Analysis
=============================================================
Performs statistical tests on telemetry data to compare WASM and Pure JS.
- Shapiro-Wilk normality check on total handshake latency
- Welch's t-test (unequal variances t-test)
- Mann-Whitney U test (non-parametric rank-sum test)
- Structured report generation for paper §IV.C
"""

import os
import sys
import glob
import numpy as np
import pandas as pd
from scipy import stats

def find_data_file():
    # Prefer v3 CSV if present
    pattern_v3 = os.path.join(os.path.dirname(__file__), '..', 'performance_data', 'starrycrypt_telemetry_v3_*.csv')
    files_v3 = sorted(glob.glob(pattern_v3))
    if files_v3:
        return files_v3[-1]

    # Fall back to v2 pattern
    pattern = os.path.join(os.path.dirname(__file__), '..', 'performance_data', 'starrycrypt_telemetry_*.csv')
    files = sorted(glob.glob(pattern))
    if not files:
        print('ERROR: No telemetry CSV found')
        sys.exit(1)
    return files[-1]

def run_tests():
    data_file = find_data_file()
    print(f"Loading telemetry file for analysis: {data_file}")
    df = pd.read_csv(data_file)

    # Filter to warm benchmark mode if mode column is present
    if 'benchmark_mode' in df.columns:
        df = df[df['benchmark_mode'] == 'warm'].copy()

    # Exclude Chrome 87 outlier per manuscript policy
    is_c87 = (df['browser_name'] == 'Chrome') & (df['browser_version'].astype(str).str.startswith('87')) & (df['os_name'] == 'macOS')
    df = df[~is_c87].copy()

    wasm_latencies = df[df['implementation'] == 'wasm']['total_handshake_mean'].dropna()
    js_latencies = df[df['implementation'] == 'pure-js']['total_handshake_mean'].dropna()

    n_wasm = len(wasm_latencies)
    n_js = len(js_latencies)

    print(f"\nSample Sizes:")
    print(f"  WASM (n={n_wasm}), Mean={wasm_latencies.mean():.4f} ms, StdDev={wasm_latencies.std():.4f} ms")
    print(f"  Pure JS (n={n_js}), Mean={js_latencies.mean():.4f} ms, StdDev={js_latencies.std():.4f} ms")

    if n_wasm < 3 or n_js < 3:
        print("\nERROR: Insufficient samples to run statistical tests (need at least 3 per group).")
        return

    # 1. Shapiro-Wilk Normality Test
    stat_w_wasm, p_w_wasm = stats.shapiro(wasm_latencies)
    stat_w_js, p_w_js = stats.shapiro(js_latencies)

    # 2. Welch's t-test (independent samples with unequal variance)
    t_stat, t_pval = stats.ttest_ind(wasm_latencies, js_latencies, equal_var=False)

    # 3. Mann-Whitney U test (non-parametric rank-sum test)
    u_stat, u_pval = stats.mannwhitneyu(wasm_latencies, js_latencies, alternative='two-sided')

    # Output structured report
    print("\n" + "="*60)
    print(" STATISTICAL ANALYSIS REPORT (§IV.C COMPATIBLE)")
    print("="*60)
    
    print("\n1. Shapiro-Wilk Normality Check:")
    print(f"  WASM:    W = {stat_w_wasm:.4f}, p = {p_w_wasm:.4e}")
    print(f"  Pure JS: W = {stat_w_js:.4f}, p = {p_w_js:.4e}")
    if p_w_wasm < 0.05 or p_w_js < 0.05:
        print("  Interpretation: Reject null hypothesis of normality (p < 0.05).")
        print("                  Data shows significant non-normality (skew/outliers).")
    else:
        print("  Interpretation: Fail to reject null hypothesis of normality (p >= 0.05).")
        print("                  Data is approximately normally distributed.")

    print("\n2. Welch's t-test (Parametric, Unequal Variance):")
    print(f"  t-statistic = {t_stat:.4f}")
    print(f"  p-value     = {t_pval:.4e}")
    if t_pval < 0.05:
        print("  Interpretation: Statistically significant difference in means (p < 0.05).")
        speedup = js_latencies.mean() / wasm_latencies.mean()
        print(f"                  WASM is on average {speedup:.2f}x faster than Pure JS.")
    else:
        print("  Interpretation: No statistically significant difference in means (p >= 0.05).")

    print("\n3. Mann-Whitney U test (Non-parametric Rank-sum):")
    print(f"  U-statistic = {u_stat:.4f}")
    print(f"  p-value     = {u_pval:.4e}")
    if u_pval < 0.05:
        print("  Interpretation: Statistically significant difference in distributions (p < 0.05).")
    else:
        print("  Interpretation: No statistically significant difference in distributions (p >= 0.05).")

    print("\n" + "="*60)
    print("END OF REPORT")
    print("="*60)

if __name__ == "__main__":
    run_tests()

