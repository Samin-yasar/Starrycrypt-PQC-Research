#!/usr/bin/env python3
"""Pure Python verification of paper claims against telemetry data."""
import csv
import math

# Read CSV
data = []
with open('performance_data/starrycrypt_telemetry_2026-05-05.csv', 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        data.append(row)

def to_float(v):
    try:
        return float(v)
    except:
        return None

# Filter implementations
wasm = [r for r in data if r.get('implementation') == 'wasm']
js = [r for r in data if r.get('implementation') == 'pure-js']

print(f"Total sessions: {len(data)}")
print(f"WASM: {len(wasm)}")
print(f"Pure JS: {len(js)}")
print()

def stats(vals):
    vals = [v for v in vals if v is not None]
    if not vals:
        return None, None, None, None, None
    n = len(vals)
    mean = sum(vals) / n
    sorted_vals = sorted(vals)
    median = sorted_vals[n // 2] if n % 2 == 1 else (sorted_vals[n // 2 - 1] + sorted_vals[n // 2]) / 2
    std = math.sqrt(sum((v - mean) ** 2 for v in vals) / n)
    p95_idx = int(0.95 * (n - 1))
    p95 = sorted_vals[min(p95_idx, n - 1)]
    return n, mean, median, std, p95

# Overall
w_t = stats([to_float(r.get('total_handshake_mean')) for r in wasm])
j_t = stats([to_float(r.get('total_handshake_mean')) for r in js])
print("=== Overall Handshake ===")
print(f"WASM  n={w_t[0]} mean={w_t[1]:.2f}ms median={w_t[2]:.2f}ms std={w_t[3]:.2f}ms p95={w_t[4]:.2f}ms")
print(f"JS    n={j_t[0]} mean={j_t[1]:.2f}ms median={j_t[2]:.2f}ms std={j_t[3]:.2f}ms p95={j_t[4]:.2f}ms")
print(f"Speedup: {j_t[1]/w_t[1]:.2f}x")
print()

# SIMD vs non-SIMD WASM
wasm_simd = [r for r in wasm if r.get('wasm_simd', '').lower() == 'true']
wasm_scalar = [r for r in wasm if r.get('wasm_simd', '').lower() == 'false']
ws_t = stats([to_float(r.get('total_handshake_mean')) for r in wasm_simd])
wl_t = stats([to_float(r.get('total_handshake_mean')) for r in wasm_scalar])
print("=== WASM SIMD ===")
print(f"SIMD    n={ws_t[0]} mean={ws_t[1]:.2f}ms median={ws_t[2]:.2f}ms std={ws_t[3]:.2f}ms")
print(f"Non-SIMD n={wl_t[0]} mean={wl_t[1]:.2f}ms median={wl_t[2]:.2f}ms std={wl_t[3]:.2f}ms")
if wl_t[0] > 0 and ws_t[1] > 0:
    print(f"Non-SIMD/SIMD ratio: {wl_t[1]/ws_t[1]:.1f}x")
print()

# Per-phase WASM
print("=== WASM Per-Phase ===")
for phase in ['mlkem_keygen_mean', 'mlkem_encaps_mean', 'mlkem_decaps_mean']:
    s = stats([to_float(r.get(phase)) for r in wasm])
    print(f"{phase}: n={s[0]} mean={s[1]:.3f}ms")
print()

# Per-phase JS
print("=== JS Per-Phase ===")
for phase in ['mlkem_keygen_mean', 'mlkem_encaps_mean', 'mlkem_decaps_mean']:
    s = stats([to_float(r.get(phase)) for r in js])
    print(f"{phase}: n={s[0]} mean={s[1]:.3f}ms")
print()

# Engine mapping
engine_map = {
    'Chrome': 'Blink', 'Google Chrome': 'Blink', 'Microsoft Edge': 'Blink',
    'Brave': 'Blink', 'Samsung Internet': 'Blink',
    'Safari': 'WebKit', 'Android WebView': 'Blink',
    'Firefox': 'Gecko'
}
print("=== Browser Engine (WASM) ===")
for eng_name in ['Blink', 'WebKit', 'Gecko']:
    sub = [r for r in wasm if engine_map.get(r.get('browser_name', ''), 'Other') == eng_name]
    s = stats([to_float(r.get('total_handshake_mean')) for r in sub])
    print(f"{eng_name}: n={s[0]} mean={s[1]:.2f}ms median={s[2]:.2f}ms")
print()

# Mobile vs Desktop
for dtype in ['mobile', 'desktop']:
    sub = [r for r in wasm if r.get('device_type') == dtype]
    s = stats([to_float(r.get('total_handshake_mean')) for r in sub])
    print(f"WASM {dtype}: n={s[0]} mean={s[1]:.2f}ms")
print()

# Device tier
print("=== Device Tier (WASM) ===")
for tier, lo, hi in [('Budget', 0, 150), ('Mid-Range', 150, 400), ('Flagship', 400, float('inf'))]:
    sub = [r for r in wasm if lo <= (to_float(r.get('baseline_mips')) or 0) < hi]
    s = stats([to_float(r.get('total_handshake_mean')) for r in sub])
    print(f"{tier}: n={s[0]} mean={s[1]:.2f}ms")
print()

# Lab vs Field
lab = [r for r in data if '[LAB]' in (r.get('device_model') or '')]
field = [r for r in data if '[LAB]' not in (r.get('device_model') or '')]
print(f"Lab sessions: {len(lab)}")
print(f"Field sessions: {len(field)}")
lab_wasm = [r for r in lab if r.get('implementation') == 'wasm']
lab_js = [r for r in lab if r.get('implementation') == 'pure-js']
field_wasm = [r for r in field if r.get('implementation') == 'wasm']
field_js = [r for r in field if r.get('implementation') == 'pure-js']
print(f"Lab WASM: {len(lab_wasm)}, Lab JS: {len(lab_js)}")
print(f"Field WASM: {len(field_wasm)}, Field JS: {len(field_js)}")
print()

# SIMD availability
simd_vals = [r.get('wasm_simd', '').lower() == 'true' for r in wasm]
threads_vals = [r.get('wasm_threads', '').lower() == 'true' for r in wasm]
bulk_vals = [r.get('wasm_bulk_memory', '').lower() == 'true' for r in wasm]
print("=== WASM Feature Availability ===")
print(f"SIMD: {sum(simd_vals)/len(simd_vals)*100:.1f}% (n={sum(simd_vals)}/{len(simd_vals)})")
print(f"Threads: {sum(threads_vals)/len(threads_vals)*100:.1f}% (n={sum(threads_vals)}/{len(threads_vals)})")
print(f"Bulk Memory: {sum(bulk_vals)/len(bulk_vals)*100:.1f}% (n={sum(bulk_vals)}/{len(bulk_vals)})")
print()

# Non-SIMD breakdown
print("=== Non-SIMD Breakdown ===")
for r in wasm_scalar:
    bn = r.get('browser_name', 'Unknown')
    os = r.get('os_name', '?')
    ver = r.get('browser_version', '?')
    val = to_float(r.get('total_handshake_mean'))
    print(f"  {bn} {ver} on {os}: {val:.3f}ms")
print()

# Check Chrome 87 outlier
chrome87 = [r for r in wasm if r.get('browser_name') == 'Chrome' and r.get('browser_version', '').startswith('87')]
if chrome87:
    v = to_float(chrome87[0].get('total_handshake_mean'))
    print(f"Chrome 87 outlier: {v:.2f}ms")
