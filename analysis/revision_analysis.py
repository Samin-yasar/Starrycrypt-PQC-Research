#!/usr/bin/env python3
"""
Comprehensive revision analysis for reviewer points M1-M5.
"""

import pandas as pd
import numpy as np
from scipy import stats

# Load data
df = pd.read_csv('performance_data/starrycrypt_telemetry_2026-05-05.csv')

wasm = df[df['implementation'] == 'wasm']
js = df[df['implementation'] == 'pure-js']

print("=" * 80)
print("M1: SAFARI NON-SIMD ANOMALY - DEEP INVESTIGATION")
print("=" * 80)

# Find all non-SIMD WASM sessions
wasm_no_simd = wasm[wasm['wasm_simd'] == False]
print(f"\nTotal non-SIMD WASM sessions: {len(wasm_no_simd)}")
print(f"\nNon-SIMD breakdown by browser:")
for browser in wasm_no_simd['browser_name'].unique():
    subset = wasm_no_simd[wasm_no_simd['browser_name'] == browser]
    print(f"\n  {browser}:")
    print(f"    n = {len(subset)}")
    for _, row in subset.iterrows():
        print(f"    - {row['browser_name']} {row['browser_version']} on {row['os_name']} {row['os_version']}")
        print(f"      latency: {row['total_handshake_mean']:.3f} ms, MIPS: {row['baseline_mips']:.1f}")
        print(f"      device: {row['device_type']}, model: {row['device_model']}")
        print(f"      threads: {row['wasm_threads']}, bulk_memory: {row['wasm_bulk_memory']}")

# Safari non-SIMD specifically
safari_no_simd = wasm_no_simd[wasm_no_simd['browser_name'].str.contains('Safari', case=False, na=False)]
print(f"\n--- Safari Non-SIMD Detailed Analysis ---")
print(f"n = {len(safari_no_simd)}")
print(f"mean latency = {safari_no_simd['total_handshake_mean'].mean():.3f} ms")
print(f"median latency = {safari_no_simd['total_handshake_mean'].median():.3f} ms")
print(f"std = {safari_no_simd['total_handshake_mean'].std():.3f} ms")
print(f"min = {safari_no_simd['total_handshake_mean'].min():.3f} ms")
print(f"max = {safari_no_simd['total_handshake_mean'].max():.3f} ms")

# SIMD-capable for comparison
wasm_simd = wasm[wasm['wasm_simd'] == True]
print(f"\n--- SIMD-Capable Comparison ---")
print(f"n = {len(wasm_simd)}")
print(f"mean latency = {wasm_simd['total_handshake_mean'].mean():.3f} ms")
print(f"median latency = {wasm_simd['total_handshake_mean'].median():.3f} ms")

print(f"\nSafari non-SIMD median ({safari_no_simd['total_handshake_mean'].median():.3f} ms) vs SIMD-capable median ({wasm_simd['total_handshake_mean'].median():.3f} ms)")
ratio = wasm_simd['total_handshake_mean'].median() / safari_no_simd['total_handshake_mean'].median()
print(f"Safari non-SIMD is {ratio:.2f}x FASTER than SIMD-capable median!")

# Chrome 87 outlier
chrome87 = wasm_no_simd[wasm_no_simd['browser_name'].str.contains('Chrome', case=False, na=False)]
if len(chrome87) > 0:
    print(f"\n--- Chrome Non-SIMD (Outlier) ---")
    print(f"n = {len(chrome87)}")
    for _, row in chrome87.iterrows():
        print(f"  Chrome {row['browser_version']} on {row['os_name']} {row['os_version']}: {row['total_handshake_mean']:.3f} ms")

# Excluding Chrome 87, non-SIMD median
no_simd_excl_chrome87 = wasm_no_simd[~(wasm_no_simd['browser_name'].str.contains('Chrome', case=False, na=False))]
print(f"\nNon-SIMD excluding Chrome 87: n={len(no_simd_excl_chrome87)}, median={no_simd_excl_chrome87['total_handshake_mean'].median():.3f} ms")

print("\n" + "=" * 80)
print("M2: BROWSER VINTAGE STRATIFICATION (Alternative to MIPS Tiers)")
print("=" * 80)

# Parse browser versions
def parse_chrome_version(v):
    if pd.isna(v) or v == 'unknown':
        return np.nan
    try:
        # Extract major version number
        return int(str(v).split('.')[0])
    except:
        return np.nan

wasm['chrome_major'] = wasm['browser_version'].apply(parse_chrome_version)

# Browser vintage categories for Chrome/Edge
# Chrome ≤100 / 101-130 / 131+
def vintage_tier(row):
    browser = str(row['browser_name']).lower()
    version = row['chrome_major']
    if pd.isna(version):
        return 'Other/Unknown'
    if 'chrome' in browser or 'edge' in browser or 'opera' in browser:
        if version <= 100:
            return 'Legacy (≤100)'
        elif version <= 130:
            return 'Mature (101-130)'
        else:
            return 'Modern (131+)'
    elif 'safari' in browser:
        return 'Safari/WebKit'
    elif 'firefox' in browser:
        return 'Firefox/Gecko'
    else:
        return 'Other'

wasm['vintage_tier'] = wasm.apply(vintage_tier, axis=1)

print("\n--- WASM Performance by Browser Vintage Tier ---")
for tier in wasm['vintage_tier'].unique():
    subset = wasm[wasm['vintage_tier'] == tier]
    if len(subset) > 0:
        print(f"\n{tier}: n={len(subset)}")
        print(f"  mean latency: {subset['total_handshake_mean'].mean():.3f} ms")
        print(f"  median latency: {subset['total_handshake_mean'].median():.3f} ms")
        print(f"  std: {subset['total_handshake_mean'].std():.3f} ms")
        print(f"  95% CI: [{subset['total_handshake_mean'].mean() - 1.96*subset['total_handshake_mean'].std()/np.sqrt(len(subset)):.3f}, "
              f"{subset['total_handshake_mean'].mean() + 1.96*subset['total_handshake_mean'].std()/np.sqrt(len(subset)):.3f}]")

# Compare MIPS-based tiers vs browser vintage
print("\n--- MIPS-Based Tiers (Original) ---")
wasm['mips_tier'] = pd.cut(wasm['baseline_mips'], bins=[-np.inf, 150, 400, np.inf], labels=['Budget(<150)', 'Mid-Range(150-400)', 'Flagship(≥400)'])
for tier in wasm['mips_tier'].unique():
    if pd.isna(tier):
        continue
    subset = wasm[wasm['mips_tier'] == tier]
    print(f"\n{tier}: n={len(subset)}")
    print(f"  mean latency: {subset['total_handshake_mean'].mean():.3f} ms")
    print(f"  median latency: {subset['total_handshake_mean'].median():.3f} ms")
    # Browser vintage distribution within this tier
    print(f"  vintage distribution:")
    for vt in subset['vintage_tier'].value_counts().index:
        count = subset['vintage_tier'].value_counts()[vt]
        print(f"    {vt}: {count} ({count/len(subset)*100:.1f}%)")

print("\n" + "=" * 80)
print("M3: CHROME 87 OUTLIER SENSITIVITY ANALYSIS")
print("=" * 80)

# Identify Chrome 87 session
chrome87_session = wasm[wasm['browser_version'].str.contains('87', na=False)]
print(f"\nChrome 87 session(s): n={len(chrome87_session)}")
if len(chrome87_session) > 0:
    for _, row in chrome87_session.iterrows():
        print(f"  {row['browser_name']} {row['browser_version']} on {row['os_name']} {row['os_version']}: {row['total_handshake_mean']:.3f} ms")

# Overall WASM stats with and without outlier
print(f"\n--- Overall WASM Stats ---")
print(f"With Chrome 87:    mean={wasm['total_handshake_mean'].mean():.3f} ms, median={wasm['total_handshake_mean'].median():.3f} ms, n={len(wasm)}")
wasm_no_outlier = wasm[~(wasm['browser_version'].str.contains('87', na=False))]
print(f"Without Chrome 87: mean={wasm_no_outlier['total_handshake_mean'].mean():.3f} ms, median={wasm_no_outlier['total_handshake_mean'].median():.3f} ms, n={len(wasm_no_outlier)}")

# Engine comparison with/without outlier
print(f"\n--- Blink Engine (Chrome/Edge/Opera) Stats ---")
blink = wasm[wasm['browser_name'].str.contains('Chrome|Edge|Opera', case=False, na=False)]
print(f"With Chrome 87:    mean={blink['total_handshake_mean'].mean():.3f} ms, n={len(blink)}")
blink_no_outlier = blink[~(blink['browser_version'].str.contains('87', na=False))]
print(f"Without Chrome 87: mean={blink_no_outlier['total_handshake_mean'].mean():.3f} ms, n={len(blink_no_outlier)}")

# SIMD/non-SIMD with/without outlier
print(f"\n--- SIMD/Non-SIMD Stats ---")
print(f"Non-SIMD with Chrome 87:    mean={wasm_no_simd['total_handshake_mean'].mean():.3f} ms, median={wasm_no_simd['total_handshake_mean'].median():.3f} ms, n={len(wasm_no_simd)}")
no_simd_no_outlier = wasm_no_simd[~(wasm_no_simd['browser_version'].str.contains('87', na=False))]
print(f"Non-SIMD without Chrome 87:   mean={no_simd_no_outlier['total_handshake_mean'].mean():.3f} ms, median={no_simd_no_outlier['total_handshake_mean'].median():.3f} ms, n={len(no_simd_no_outlier)}")

# Mobile vs Desktop with/without outlier
print(f"\n--- Mobile vs Desktop ---")
mobile = wasm[wasm['device_type'] == 'mobile']
desktop = wasm[wasm['device_type'] == 'desktop']
mobile_no87 = mobile[~(mobile['browser_version'].str.contains('87', na=False))]
desktop_no87 = desktop[~(desktop['browser_version'].str.contains('87', na=False))]
print(f"Mobile with Chrome 87:    mean={mobile['total_handshake_mean'].mean():.3f} ms, n={len(mobile)}")
print(f"Mobile without Chrome 87: mean={mobile_no87['total_handshake_mean'].mean():.3f} ms, n={len(mobile_no87)}")
print(f"Desktop with Chrome 87:    mean={desktop['total_handshake_mean'].mean():.3f} ms, n={len(desktop)}")
print(f"Desktop without Chrome 87: mean={desktop_no87['total_handshake_mean'].mean():.3f} ms, n={len(desktop_no87)}")

# Statistical test: impact on WASM vs JS
print(f"\n--- WASM vs JS Sensitivity ---")
js_data = df[df['implementation'] == 'pure-js']['total_handshake_mean'].dropna()
wasm_data = wasm['total_handshake_mean'].dropna()
wasm_no87_data = wasm_no_outlier['total_handshake_mean'].dropna()

# With outlier
t1, p1 = stats.ttest_ind(wasm_data, js_data, equal_var=False)
print(f"With Chrome 87:    t={t1:.3f}, p={p1:.4f}")
# Without outlier
t2, p2 = stats.ttest_ind(wasm_no87_data, js_data, equal_var=False)
print(f"Without Chrome 87: t={t2:.3f}, p={p2:.4f}")

print("\n" + "=" * 80)
print("M5: FIELD DATA ANALYSIS")
print("=" * 80)

field = df[df['device_model'] != '[LAB]']
lab = df[df['device_model'] == '[LAB]']

print(f"\nField sessions: {len(field)} (WASM: {len(field[field['implementation']=='wasm'])}, JS: {len(field[field['implementation']=='pure-js'])})")
print(f"Lab sessions: {len(lab)} (WASM: {len(lab[lab['implementation']=='wasm'])}, JS: {len(lab[lab['implementation']=='pure-js'])})")

field_wasm = field[field['implementation'] == 'wasm']
field_js = field[field['implementation'] == 'pure-js']

print(f"\n--- Field WASM Performance ---")
print(f"mean: {field_wasm['total_handshake_mean'].mean():.3f} ms")
print(f"median: {field_wasm['total_handshake_mean'].median():.3f} ms")
print(f"std: {field_wasm['total_handshake_mean'].std():.3f} ms")

print(f"\n--- Field JS Performance ---")
print(f"mean: {field_js['total_handshake_mean'].mean():.3f} ms")
print(f"median: {field_js['total_handshake_mean'].median():.3f} ms")
print(f"std: {field_js['total_handshake_mean'].std():.3f} ms")

print(f"\n--- Field Browser Distribution ---")
print(field_wasm['browser_name'].value_counts())

print(f"\n--- Field OS Distribution ---")
print(field_wasm['os_name'].value_counts())

print(f"\n--- Field Device Type ---")
print(field_wasm['device_type'].value_counts())

# App browser vs standalone browser heuristic
# In field data, app browsers often report specific strings
print(f"\n--- App Browser vs Standalone Browser (Field WASM) ---")
# Heuristic: if browser_name contains common app browser patterns
app_patterns = ['FBAN', 'FBAV', 'Instagram', 'LinkedIn', 'Twitter', 'WhatsApp', 'WeChat']
# Actually let's just look at what's in the data
print("Browser versions in field WASM:")
for browser in field_wasm['browser_name'].unique():
    subset = field_wasm[field_wasm['browser_name'] == browser]
    print(f"  {browser}: n={len(subset)}, mean={subset['total_handshake_mean'].mean():.3f} ms")

# SIMD in field data
print(f"\n--- Field WASM SIMD Availability ---")
print(f"SIMD: {field_wasm['wasm_simd'].mean()*100:.1f}%")
print(f"Threads: {field_wasm['wasm_threads'].mean()*100:.1f}%")

# MIPS distribution in field
print(f"\n--- Field MIPS Distribution ---")
print(f"mean MIPS: {field_wasm['baseline_mips'].mean():.1f}")
print(f"median MIPS: {field_wasm['baseline_mips'].median():.1f}")
print(f"min MIPS: {field_wasm['baseline_mips'].min():.1f}")
print(f"max MIPS: {field_wasm['baseline_mips'].max():.1f}")

print("\n" + "=" * 80)
print("SUMMARY TABLE FOR PAPER")
print("=" * 80)

print("\n--- Sensitivity Analysis Table ---")
print("Metric                    | With C87    | Without C87 | Impact")
print("-" * 65)
print(f"WASM mean (ms)            | {wasm['total_handshake_mean'].mean():.3f}       | {wasm_no_outlier['total_handshake_mean'].mean():.3f}       | {(wasm['total_handshake_mean'].mean() / wasm_no_outlier['total_handshake_mean'].mean() - 1)*100:.1f}% inflation")
print(f"WASM median (ms)          | {wasm['total_handshake_mean'].median():.3f}       | {wasm_no_outlier['total_handshake_mean'].median():.3f}       | negligible")
print(f"Blink mean (ms)           | {blink['total_handshake_mean'].mean():.3f}       | {blink_no_outlier['total_handshake_mean'].mean():.3f}       | {(blink['total_handshake_mean'].mean() / blink_no_outlier['total_handshake_mean'].mean() - 1)*100:.1f}% inflation")
print(f"Non-SIMD mean (ms)        | {wasm_no_simd['total_handshake_mean'].mean():.3f}     | {no_simd_no_outlier['total_handshake_mean'].mean():.3f}       | {(wasm_no_simd['total_handshake_mean'].mean() / no_simd_no_outlier['total_handshake_mean'].mean() - 1)*100:.1f}% inflation")
print(f"Desktop mean (ms)         | {desktop['total_handshake_mean'].mean():.3f}       | {desktop_no87['total_handshake_mean'].mean():.3f}       | {(desktop['total_handshake_mean'].mean() / desktop_no87['total_handshake_mean'].mean() - 1)*100:.1f}% inflation")
print(f"WASM vs JS t-stat         | {t1:.3f}       | {t2:.3f}       | p shifts {p1:.4f} -> {p2:.4f}")
