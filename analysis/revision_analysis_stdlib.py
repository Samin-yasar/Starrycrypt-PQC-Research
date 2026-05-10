#!/usr/bin/env python3
"""
Comprehensive revision analysis for reviewer points M1-M5.
Uses only standard library (no pandas/scipy dependency).
"""

import csv
import math
from collections import defaultdict

def load_data(filepath):
    rows = []
    with open(filepath, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Convert numeric fields
            for key in ['baseline_mips', 'total_handshake_mean', 'mlkem_keygen_mean',
                        'mlkem_encaps_mean', 'mlkem_decaps_mean', 'logical_cores', 'ram_gib',
                        'timer_precision_ms']:
                try:
                    row[key] = float(row[key]) if row[key] else 0.0
                except:
                    row[key] = 0.0
            # Convert booleans
            for key in ['wasm_simd', 'wasm_threads', 'wasm_bulk_memory', 'wasm_relaxed_simd', 'tab_visible']:
                row[key] = row[key].lower() == 'true'
            rows.append(row)
    return rows

def mean(data):
    return sum(data) / len(data) if data else 0.0

def median(data):
    s = sorted(data)
    n = len(s)
    if n == 0:
        return 0.0
    if n % 2 == 1:
        return s[n // 2]
    return (s[n // 2 - 1] + s[n // 2]) / 2

def std(data):
    if len(data) < 2:
        return 0.0
    m = mean(data)
    return math.sqrt(sum((x - m) ** 2 for x in data) / (len(data) - 1))

def ci95(data):
    if len(data) < 2:
        return (0.0, 0.0)
    m = mean(data)
    s = std(data)
    margin = 1.96 * s / math.sqrt(len(data))
    return (m - margin, m + margin)

# Welch's t-test approximation
def welch_ttest(a, b):
    m1, m2 = mean(a), mean(b)
    s1, s2 = std(a), std(b)
    n1, n2 = len(a), len(b)
    se = math.sqrt(s1**2/n1 + s2**2/n2)
    t = (m1 - m2) / se if se > 0 else 0.0
    # Satterthwaite df approximation
    num = (s1**2/n1 + s2**2/n2)**2
    den = (s1**2/n1)**2/(n1-1) + (s2**2/n2)**2/(n2-1)
    df = num / den if den > 0 else n1 + n2 - 2
    return t, df

rows = load_data('performance_data/starrycrypt_telemetry_2026-05-05.csv')

wasm = [r for r in rows if r['implementation'] == 'wasm']
js = [r for r in rows if r['implementation'] == 'pure-js']
field = [r for r in rows if r['device_model'] != '[LAB]']
lab = [r for r in rows if r['device_model'] == '[LAB]']

print("=" * 80)
print("M1: SAFARI NON-SIMD ANOMALY - DEEP INVESTIGATION")
print("=" * 80)

wasm_no_simd = [r for r in wasm if not r['wasm_simd']]
print(f"\nTotal non-SIMD WASM sessions: {len(wasm_no_simd)}")

by_browser = defaultdict(list)
for r in wasm_no_simd:
    by_browser[r['browser_name']].append(r)

for browser, items in sorted(by_browser.items()):
    latencies = [r['total_handshake_mean'] for r in items]
    print(f"\n  {browser}: n={len(items)}, mean={mean(latencies):.3f}ms, median={median(latencies):.3f}ms")
    for r in items:
        print(f"    - {r['browser_name']} {r['browser_version']} on {r['os_name']} {r['os_version']}")
        print(f"      latency={r['total_handshake_mean']:.3f}ms, MIPS={r['baseline_mips']:.1f}, device={r['device_type']}")
        print(f"      threads={r['wasm_threads']}, bulk_mem={r['wasm_bulk_memory']}, model={r['device_model']}")

# Safari non-SIMD
safari_no_simd = [r for r in wasm_no_simd if 'safari' in r['browser_name'].lower()]
if safari_no_simd:
    lat = [r['total_handshake_mean'] for r in safari_no_simd]
    print(f"\n--- Safari Non-SIMD ---")
    print(f"n={len(safari_no_simd)}, mean={mean(lat):.3f}ms, median={median(lat):.3f}ms, std={std(lat):.3f}ms")
    print(f"min={min(lat):.3f}ms, max={max(lat):.3f}ms")

wasm_simd = [r for r in wasm if r['wasm_simd']]
if wasm_simd:
    lat = [r['total_handshake_mean'] for r in wasm_simd]
    print(f"\n--- SIMD-Capable ---")
    print(f"n={len(wasm_simd)}, mean={mean(lat):.3f}ms, median={median(lat):.3f}ms")
    saf_lat = [r['total_handshake_mean'] for r in safari_no_simd]
    if saf_lat and lat:
        ratio = median(lat) / median(saf_lat)
        print(f"Safari non-SIMD median ({median(saf_lat):.3f}ms) vs SIMD-capable median ({median(lat):.3f}ms)")
        print(f"Safari non-SIMD is {ratio:.2f}x FASTER")

# Non-SIMD excluding Chrome 87
no_simd_no_chrome87 = [r for r in wasm_no_simd if not ('87' in str(r['browser_version']))]
if no_simd_no_chrome87:
    lat = [r['total_handshake_mean'] for r in no_simd_no_chrome87]
    print(f"\nNon-SIMD excluding Chrome 87: n={len(no_simd_no_chrome87)}, median={median(lat):.3f}ms")

print("\n" + "=" * 80)
print("M2: BROWSER VINTAGE STRATIFICATION")
print("=" * 80)

def parse_chrome_major(v):
    if not v or v == 'unknown':
        return None
    try:
        return int(str(v).split('.')[0])
    except:
        return None

def vintage_tier(r):
    browser = r['browser_name'].lower()
    major = parse_chrome_major(r['browser_version'])
    if major is None:
        return 'Other/Unknown'
    if any(x in browser for x in ['chrome', 'edge', 'opera', 'brave']):
        if major <= 100:
            return 'Legacy (≤100)'
        elif major <= 130:
            return 'Mature (101-130)'
        else:
            return 'Modern (131+)'
    elif 'safari' in browser:
        return 'Safari/WebKit'
    elif 'firefox' in browser:
        return 'Firefox/Gecko'
    return 'Other'

vintage_groups = defaultdict(list)
for r in wasm:
    vintage_groups[vintage_tier(r)].append(r)

print("\n--- WASM by Browser Vintage ---")
for tier in sorted(vintage_groups.keys()):
    items = vintage_groups[tier]
    lat = [r['total_handshake_mean'] for r in items]
    c = ci95(lat)
    print(f"\n{tier}: n={len(items)}")
    print(f"  mean={mean(lat):.3f}ms, median={median(lat):.3f}ms, std={std(lat):.3f}ms")
    print(f"  95% CI: [{c[0]:.3f}, {c[1]:.3f}]")

# MIPS-based tiers
mips_groups = defaultdict(list)
for r in wasm:
    mips = r['baseline_mips']
    if mips < 150:
        mips_groups['Budget(<150)'].append(r)
    elif mips < 400:
        mips_groups['Mid-Range(150-400)'].append(r)
    else:
        mips_groups['Flagship(≥400)'].append(r)

print("\n--- MIPS-Based Tiers ---")
for tier in ['Budget(<150)', 'Mid-Range(150-400)', 'Flagship(≥400)']:
    items = mips_groups.get(tier, [])
    if not items:
        continue
    lat = [r['total_handshake_mean'] for r in items]
    print(f"\n{tier}: n={len(items)}, mean={mean(lat):.3f}ms, median={median(lat):.3f}ms")
    vdist = defaultdict(int)
    for r in items:
        vdist[vintage_tier(r)] += 1
    print(f"  vintage distribution:")
    for vt, cnt in sorted(vdist.items()):
        print(f"    {vt}: {cnt} ({cnt/len(items)*100:.1f}%)")

print("\n" + "=" * 80)
print("M3: CHROME 87 OUTLIER SENSITIVITY ANALYSIS")
print("=" * 80)

chrome87 = [r for r in wasm if '87' in str(r['browser_version'])]
print(f"\nChrome 87 session(s): n={len(chrome87)}")
for r in chrome87:
    print(f"  {r['browser_name']} {r['browser_version']} on {r['os_name']} {r['os_version']}: {r['total_handshake_mean']:.3f}ms")

wasm_no87 = [r for r in wasm if not ('87' in str(r['browser_version']))]

lat_all = [r['total_handshake_mean'] for r in wasm]
lat_no87 = [r['total_handshake_mean'] for r in wasm_no87]
print(f"\nWASM with Chrome 87:    mean={mean(lat_all):.3f}ms, median={median(lat_all):.3f}ms, n={len(lat_all)}")
print(f"WASM without Chrome 87: mean={mean(lat_no87):.3f}ms, median={median(lat_no87):.3f}ms, n={len(lat_no87)}")

# Blink
blink_all = [r for r in wasm if any(x in r['browser_name'].lower() for x in ['chrome', 'edge', 'opera', 'brave'])]
blink_no87 = [r for r in blink_all if not ('87' in str(r['browser_version']))]
lat_b_all = [r['total_handshake_mean'] for r in blink_all]
lat_b_no87 = [r['total_handshake_mean'] for r in blink_no87]
print(f"\nBlink with Chrome 87:    mean={mean(lat_b_all):.3f}ms, n={len(lat_b_all)}")
print(f"Blink without Chrome 87: mean={mean(lat_b_no87):.3f}ms, n={len(lat_b_no87)}")

# Non-SIMD
lat_ns_all = [r['total_handshake_mean'] for r in wasm_no_simd]
lat_ns_no87 = [r['total_handshake_mean'] for r in no_simd_no_chrome87]
print(f"\nNon-SIMD with Chrome 87:    mean={mean(lat_ns_all):.3f}ms, median={median(lat_ns_all):.3f}ms, n={len(lat_ns_all)}")
print(f"Non-SIMD without Chrome 87: mean={mean(lat_ns_no87):.3f}ms, median={median(lat_ns_no87):.3f}ms, n={len(lat_ns_no87)}")

# Mobile/desktop
mobile_all = [r for r in wasm if r['device_type'] == 'mobile']
desktop_all = [r for r in wasm if r['device_type'] == 'desktop']
mobile_no87 = [r for r in mobile_all if not ('87' in str(r['browser_version']))]
desktop_no87 = [r for r in desktop_all if not ('87' in str(r['browser_version']))]
print(f"\nMobile with Chrome 87:    mean={mean([r['total_handshake_mean'] for r in mobile_all]):.3f}ms, n={len(mobile_all)}")
print(f"Mobile without Chrome 87: mean={mean([r['total_handshake_mean'] for r in mobile_no87]):.3f}ms, n={len(mobile_no87)}")
print(f"Desktop with Chrome 87:    mean={mean([r['total_handshake_mean'] for r in desktop_all]):.3f}ms, n={len(desktop_all)}")
print(f"Desktop without Chrome 87: mean={mean([r['total_handshake_mean'] for r in desktop_no87]):.3f}ms, n={len(desktop_no87)}")

# WASM vs JS sensitivity
js_lat = [r['total_handshake_mean'] for r in js]
print(f"\n--- WASM vs JS Welch's t-test ---")
t1, df1 = welch_ttest([r['total_handshake_mean'] for r in wasm], js_lat)
t2, df2 = welch_ttest([r['total_handshake_mean'] for r in wasm_no87], js_lat)
print(f"With Chrome 87:    t={t1:.3f}, df={df1:.1f}")
print(f"Without Chrome 87: t={t2:.3f}, df={df2:.1f}")

print("\n" + "=" * 80)
print("M5: FIELD DATA ANALYSIS")
print("=" * 80)

field_wasm = [r for r in field if r['implementation'] == 'wasm']
field_js = [r for r in field if r['implementation'] == 'pure-js']
print(f"\nField sessions: {len(field)} (WASM: {len(field_wasm)}, JS: {len(field_js)})")
print(f"Lab sessions: {len(lab)} (WASM: {len([r for r in lab if r['implementation']=='wasm'])}, JS: {len([r for r in lab if r['implementation']=='pure-js'])})")

fw_lat = [r['total_handshake_mean'] for r in field_wasm]
fj_lat = [r['total_handshake_mean'] for r in field_js]
print(f"\nField WASM: mean={mean(fw_lat):.3f}ms, median={median(fw_lat):.3f}ms, std={std(fw_lat):.3f}ms, n={len(fw_lat)}")
print(f"Field JS:   mean={mean(fj_lat):.3f}ms, median={median(fj_lat):.3f}ms, std={std(fj_lat):.3f}ms, n={len(fj_lat)}")

# Browser distribution in field
print(f"\n--- Field WASM Browser Distribution ---")
fb = defaultdict(list)
for r in field_wasm:
    fb[r['browser_name']].append(r)
for browser, items in sorted(fb.items(), key=lambda x: -len(x[1])):
    lat = [r['total_handshake_mean'] for r in items]
    print(f"  {browser}: n={len(items)}, mean={mean(lat):.3f}ms, median={median(lat):.3f}ms")

# OS distribution
print(f"\n--- Field WASM OS Distribution ---")
fo = defaultdict(list)
for r in field_wasm:
    fo[r['os_name']].append(r)
for os, items in sorted(fo.items(), key=lambda x: -len(x[1])):
    print(f"  {os}: n={len(items)}")

# Device type
print(f"\n--- Field WASM Device Type ---")
fd = defaultdict(list)
for r in field_wasm:
    fd[r['device_type']].append(r)
for dt, items in sorted(fd.items(), key=lambda x: -len(x[1])):
    lat = [r['total_handshake_mean'] for r in items]
    print(f"  {dt}: n={len(items)}, mean={mean(lat):.3f}ms")

# SIMD in field
fsimd = sum(1 for r in field_wasm if r['wasm_simd'])
fthreads = sum(1 for r in field_wasm if r['wasm_threads'])
print(f"\n--- Field WASM Feature Availability ---")
print(f"SIMD: {fsimd}/{len(field_wasm)} ({fsimd/len(field_wasm)*100:.1f}%)")
print(f"Threads: {fthreads}/{len(field_wasm)} ({fthreads/len(field_wasm)*100:.1f}%)")

# MIPS in field
fmips = [r['baseline_mips'] for r in field_wasm if r['baseline_mips'] > 0]
print(f"\n--- Field MIPS Distribution ---")
print(f"mean={mean(fmips):.1f}, median={median(fmips):.1f}, min={min(fmips):.1f}, max={max(fmips):.1f}")

# Lab vs field comparison
lw = [r for r in lab if r['implementation'] == 'wasm']
lw_lat = [r['total_handshake_mean'] for r in lw]
print(f"\n--- Lab vs Field WASM ---")
print(f"Lab WASM:   mean={mean(lw_lat):.3f}ms, median={median(lw_lat):.3f}ms, n={len(lw_lat)}")
print(f"Field WASM: mean={mean(fw_lat):.3f}ms, median={median(fw_lat):.3f}ms, n={len(fw_lat)}")

# Summary table
print("\n" + "=" * 80)
print("SUMMARY TABLE: CHROME 87 SENSITIVITY")
print("=" * 80)
print(f"\n{'Metric':<30} {'With C87':>12} {'Without C87':>14} {'Inflation':>12}")
print("-" * 70)

def pct_inflation(with_val, without_val):
    if without_val == 0:
        return "N/A"
    return f"{(with_val/without_val - 1)*100:.1f}%"

print(f"{'WASM mean (ms)':<30} {mean(lat_all):>12.3f} {mean(lat_no87):>14.3f} {pct_inflation(mean(lat_all), mean(lat_no87)):>12}")
print(f"{'WASM median (ms)':<30} {median(lat_all):>12.3f} {median(lat_no87):>14.3f} {pct_inflation(median(lat_all), median(lat_no87)):>12}")
print(f"{'Blink mean (ms)':<30} {mean(lat_b_all):>12.3f} {mean(lat_b_no87):>14.3f} {pct_inflation(mean(lat_b_all), mean(lat_b_no87)):>12}")
print(f"{'Non-SIMD mean (ms)':<30} {mean(lat_ns_all):>12.3f} {mean(lat_ns_no87):>14.3f} {pct_inflation(mean(lat_ns_all), mean(lat_ns_no87)):>12}")
print(f"{'Desktop mean (ms)':<30} {mean([r['total_handshake_mean'] for r in desktop_all]):>12.3f} {mean([r['total_handshake_mean'] for r in desktop_no87]):>14.3f} {pct_inflation(mean([r['total_handshake_mean'] for r in desktop_all]), mean([r['total_handshake_mean'] for r in desktop_no87])):>12}")
print(f"{'WASM vs JS t':<30} {t1:>12.3f} {t2:>14.3f} {'p shifts':>12}")
