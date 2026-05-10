#!/usr/bin/env python3
"""
Corrected revision analysis for reviewer points M1-M5.
Properly classifies lab vs field using device_model.startswith('[LAB]').
"""

import csv
import math
from collections import defaultdict

def load_data(filepath):
    rows = []
    with open(filepath, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            for key in ['baseline_mips', 'total_handshake_mean', 'mlkem_keygen_mean',
                        'mlkem_encaps_mean', 'mlkem_decaps_mean', 'logical_cores', 'ram_gib',
                        'timer_precision_ms']:
                try:
                    row[key] = float(row[key]) if row[key] else 0.0
                except:
                    row[key] = 0.0
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

def welch_ttest(a, b):
    m1, m2 = mean(a), mean(b)
    s1, s2 = std(a), std(b)
    n1, n2 = len(a), len(b)
    se = math.sqrt(s1**2/n1 + s2**2/n2)
    t = (m1 - m2) / se if se > 0 else 0.0
    num = (s1**2/n1 + s2**2/n2)**2
    den = (s1**2/n1)**2/(n1-1) + (s2**2/n2)**2/(n2-1)
    df = num / den if den > 0 else n1 + n2 - 2
    return t, df

rows = load_data('performance_data/starrycrypt_telemetry_2026-05-05.csv')

# Correct lab/field classification
lab = [r for r in rows if r['device_model'].startswith('[LAB]')]
field = [r for r in rows if not r['device_model'].startswith('[LAB]')]

print(f"Total: {len(rows)}")
print(f"Lab: {len(lab)}")
print(f"Field: {len(field)}")

wasm = [r for r in rows if r['implementation'] == 'wasm']
js = [r for r in rows if r['implementation'] == 'pure-js']

field_wasm = [r for r in field if r['implementation'] == 'wasm']
field_js = [r for r in field if r['implementation'] == 'pure-js']
lab_wasm = [r for r in lab if r['implementation'] == 'wasm']
lab_js = [r for r in lab if r['implementation'] == 'pure-js']

print(f"\nLab WASM: {len(lab_wasm)}, Lab JS: {len(lab_js)}")
print(f"Field WASM: {len(field_wasm)}, Field JS: {len(field_js)}")

print("\n" + "=" * 80)
print("M5: FIELD DATA ANALYSIS (CORRECTED)")
print("=" * 80)

fw_lat = [r['total_handshake_mean'] for r in field_wasm]
fj_lat = [r['total_handshake_mean'] for r in field_js]
lw_lat = [r['total_handshake_mean'] for r in lab_wasm]
lj_lat = [r['total_handshake_mean'] for r in lab_js]

print(f"\nField WASM: mean={mean(fw_lat):.3f}ms, median={median(fw_lat):.3f}ms, std={std(fw_lat):.3f}ms, n={len(fw_lat)}")
print(f"Field JS:   mean={mean(fj_lat):.3f}ms, median={median(fj_lat):.3f}ms, std={std(fj_lat):.3f}ms, n={len(fj_lat)}")
print(f"Lab WASM:   mean={mean(lw_lat):.3f}ms, median={median(lw_lat):.3f}ms, std={std(lw_lat):.3f}ms, n={len(lw_lat)}")
print(f"Lab JS:     mean={mean(lj_lat):.3f}ms, median={median(lj_lat):.3f}ms, std={std(lj_lat):.3f}ms, n={len(lj_lat)}")

if fw_lat and fj_lat:
    print(f"Field speedup (mean): {mean(fj_lat)/mean(fw_lat):.2f}x")
    print(f"Field speedup (median): {median(fj_lat)/median(fw_lat):.2f}x")

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
    lat = [r['total_handshake_mean'] for r in items]
    print(f"  {os}: n={len(items)}, mean={mean(lat):.3f}ms")

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

# App browser vs standalone browser
print(f"\n--- Field User-Agent Patterns (heuristic app-browser detection) ---")
for r in field_wasm[:20]:
    ua = r.get('user_agent', '')
    # We don't have user_agent in the CSV, so skip this
    pass

# Check for specific app browsers by browser_name
app_browsers = ['Android WebView', 'Samsung Internet']
for ab in app_browsers:
    items = [r for r in field_wasm if ab in r['browser_name']]
    if items:
        lat = [r['total_handshake_mean'] for r in items]
        print(f"  {ab}: n={len(items)}, mean={mean(lat):.3f}ms")

# Check for specific device models in field (SoC proxy)
print(f"\n--- Field Device Models (top 15) ---")
models = defaultdict(list)
for r in field_wasm:
    models[r['device_model']].append(r)
for model, items in sorted(models.items(), key=lambda x: -len(x[1]))[:15]:
    lat = [r['total_handshake_mean'] for r in items]
    print(f"  {model}: n={len(items)}, mean={mean(lat):.3f}ms")

# Performance by OS + device type
print(f"\n--- Field Performance by OS + Device Type ---")
combo = defaultdict(list)
for r in field_wasm:
    key = f"{r['os_name']}/{r['device_type']}"
    combo[key].append(r)
for key, items in sorted(combo.items(), key=lambda x: -len(x[1])):
    lat = [r['total_handshake_mean'] for r in items]
    print(f"  {key}: n={len(items)}, mean={mean(lat):.3f}ms, median={median(lat):.3f}ms")

# Non-SIMD in field
field_no_simd = [r for r in field_wasm if not r['wasm_simd']]
print(f"\n--- Field Non-SIMD WASM ---")
print(f"n={len(field_no_simd)}")
for r in field_no_simd:
    print(f"  {r['browser_name']} {r['browser_version']} on {r['os_name']}: {r['total_handshake_mean']:.3f}ms")
