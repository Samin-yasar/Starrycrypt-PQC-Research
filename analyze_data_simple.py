#!/usr/bin/env python3
import csv
import statistics

# Load the performance data
data = []
with open('performance_data/starrycrypt_telemetry_2026-05-03.csv', 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        data.append(row)

print("=== Dataset Overview ===")
print(f"Total sessions: {len(data)}")

wasm_data = [row for row in data if row['implementation'] == 'wasm']
js_data = [row for row in data if row['implementation'] == 'pure-js']

print(f"WASM sessions: {len(wasm_data)}")
print(f"Pure JS sessions: {len(js_data)}")
print()

# Overall statistics
wasm_handshakes = [float(row['total_handshake_mean']) for row in wasm_data]
js_handshakes = [float(row['total_handshake_mean']) for row in js_data]

print("=== Overall Performance ===")
print(f"WASM mean handshake: {statistics.mean(wasm_handshakes):.2f}ms")
print(f"WASM median handshake: {statistics.median(wasm_handshakes):.2f}ms")
print(f"JS mean handshake: {statistics.mean(js_handshakes):.2f}ms")
print(f"JS median handshake: {statistics.median(js_handshakes):.2f}ms")
print(f"Overall speedup: {statistics.mean(js_handshakes) / statistics.mean(wasm_handshakes):.2f}x")
print()

# SIMD vs non-SIMD WASM
wasm_simd = [row for row in wasm_data if row['wasm_simd'] == 'true']
wasm_scalar = [row for row in wasm_data if row['wasm_simd'] == 'false']

wasm_simd_handshakes = [float(row['total_handshake_mean']) for row in wasm_simd]
wasm_scalar_handshakes = [float(row['total_handshake_mean']) for row in wasm_scalar]

print("=== WASM SIMD Analysis ===")
print(f"SIMD sessions: {len(wasm_simd)}")
print(f"Scalar (no SIMD) sessions: {len(wasm_scalar)}")
print(f"SIMD mean: {statistics.mean(wasm_simd_handshakes):.2f}ms")
print(f"Scalar mean: {statistics.mean(wasm_scalar_handshakes):.2f}ms")
if len(wasm_scalar) > 0 and statistics.mean(wasm_scalar_handshakes) > 0:
    print(f"SIMD speedup: {statistics.mean(wasm_scalar_handshakes) / statistics.mean(wasm_simd_handshakes):.1f}x")
print()

# Per-phase statistics for WASM
wasm_keygen = [float(row['mlkem_keygen_mean']) for row in wasm_data]
wasm_encaps = [float(row['mlkem_encaps_mean']) for row in wasm_data]
wasm_decaps = [float(row['mlkem_decaps_mean']) for row in wasm_data]

print("=== WASM Per-Phase Performance ===")
print(f"KeyGen mean: {statistics.mean(wasm_keygen):.3f}ms")
print(f"Encaps mean: {statistics.mean(wasm_encaps):.3f}ms")
print(f"Decaps mean: {statistics.mean(wasm_decaps):.3f}ms")
print()

# Per-phase statistics for JS
js_keygen = [float(row['mlkem_keygen_mean']) for row in js_data]
js_encaps = [float(row['mlkem_encaps_mean']) for row in js_data]
js_decaps = [float(row['mlkem_decaps_mean']) for row in js_data]

print("=== JS Per-Phase Performance ===")
print(f"KeyGen mean: {statistics.mean(js_keygen):.3f}ms")
print(f"Encaps mean: {statistics.mean(js_encaps):.3f}ms")
print(f"Decaps mean: {statistics.mean(js_decaps):.3f}ms")
print()

# Browser engine analysis
def categorize_engine(browser_name):
    if browser_name in ['Chrome', 'Google Chrome', 'Microsoft Edge', 'Brave']:
        return 'Blink'
    elif browser_name in ['Safari', 'Samsung Internet']:
        return 'WebKit'
    elif browser_name == 'Firefox':
        return 'Gecko'
    else:
        return 'Other'

engines = {}
for row in wasm_data:
    engine = categorize_engine(row['browser_name'])
    if engine != 'Other':
        if engine not in engines:
            engines[engine] = []
        engines[engine].append(float(row['total_handshake_mean']))

print("=== Browser Engine Analysis ===")
for engine, handshakes in engines.items():
    print(f"{engine}: {statistics.mean(handshakes):.2f}ms (n={len(handshakes)})")
print()

# Device type analysis
mobile_wasm = [row for row in wasm_data if row['device_type'] == 'mobile']
desktop_wasm = [row for row in wasm_data if row['device_type'] == 'desktop']

mobile_wasm_handshakes = [float(row['total_handshake_mean']) for row in mobile_wasm]
desktop_wasm_handshakes = [float(row['total_handshake_mean']) for row in desktop_wasm]

print("=== Mobile vs Desktop ===")
print(f"Mobile WASM: {statistics.mean(mobile_wasm_handshakes):.2f}ms (n={len(mobile_wasm)})")
print(f"Desktop WASM: {statistics.mean(desktop_wasm_handshakes):.2f}ms (n={len(desktop_wasm)})")
print()

# Check for field vs lab data
field_data = [row for row in data if '[LAB]' not in row['device_model']]
lab_data = [row for row in data if '[LAB]' in row['device_model']]

print("=== Field vs Lab Data ===")
print(f"Field sessions: {len(field_data)}")
print(f"Lab sessions: {len(lab_data)}")
print(f"Total: {len(field_data) + len(lab_data)}")
print()

# WASM capability statistics
simd_count = sum(1 for row in wasm_data if row['wasm_simd'] == 'true')
threads_count = sum(1 for row in wasm_data if row['wasm_threads'] == 'true')
bulk_memory_count = sum(1 for row in wasm_data if row['wasm_bulk_memory'] == 'true')

print("=== WASM Feature Availability ===")
print(f"SIMD: {simd_count/len(wasm_data)*100:.1f}%")
print(f"Threads: {threads_count/len(wasm_data)*100:.1f}%")
print(f"Bulk Memory: {bulk_memory_count/len(wasm_data)*100:.1f}%")
