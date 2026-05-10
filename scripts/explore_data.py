#!/usr/bin/env python3
import pandas as pd
import numpy as np

# Load the performance data
df = pd.read_csv('performance_data/starrycrypt_telemetry_2026-05-05.csv')

print("=== Dataset Overview ===")
print(f"Total sessions: {len(df)}")
print(f"WASM sessions: {len(df[df['implementation'] == 'wasm'])}")
print(f"Pure JS sessions: {len(df[df['implementation'] == 'pure-js'])}")
print()

# Overall statistics
wasm_data = df[df['implementation'] == 'wasm']
js_data = df[df['implementation'] == 'pure-js']

print("=== Overall Performance ===")
print(f"WASM mean handshake: {wasm_data['total_handshake_mean'].mean():.2f}ms")
print(f"WASM median handshake: {wasm_data['total_handshake_mean'].median():.2f}ms")
print(f"JS mean handshake: {js_data['total_handshake_mean'].mean():.2f}ms")
print(f"JS median handshake: {js_data['total_handshake_mean'].median():.2f}ms")
print(f"Overall speedup: {js_data['total_handshake_mean'].mean() / wasm_data['total_handshake_mean'].mean():.2f}x")
print()

# SIMD vs non-SIMD WASM
wasm_simd = wasm_data[wasm_data['wasm_simd'] == True]
wasm_scalar = wasm_data[wasm_data['wasm_simd'] == False]

print("=== WASM SIMD Analysis ===")
print(f"SIMD sessions: {len(wasm_simd)}")
print(f"Scalar (no SIMD) sessions: {len(wasm_scalar)}")
print(f"SIMD mean: {wasm_simd['total_handshake_mean'].mean():.2f}ms")
print(f"Scalar mean: {wasm_scalar['total_handshake_mean'].mean():.2f}ms")
if len(wasm_scalar) > 0 and wasm_scalar['total_handshake_mean'].mean() > 0:
    print(f"SIMD speedup: {wasm_scalar['total_handshake_mean'].mean() / wasm_simd['total_handshake_mean'].mean():.1f}x")
print()

# Per-phase statistics for WASM
print("=== WASM Per-Phase Performance ===")
print(f"KeyGen mean: {wasm_data['mlkem_keygen_mean'].mean():.3f}ms")
print(f"Encaps mean: {wasm_data['mlkem_encaps_mean'].mean():.3f}ms")
print(f"Decaps mean: {wasm_data['mlkem_decaps_mean'].mean():.3f}ms")
print()

# Per-phase statistics for JS
print("=== JS Per-Phase Performance ===")
print(f"KeyGen mean: {js_data['mlkem_keygen_mean'].mean():.3f}ms")
print(f"Encaps mean: {js_data['mlkem_encaps_mean'].mean():.3f}ms")
print(f"Decaps mean: {js_data['mlkem_decaps_mean'].mean():.3f}ms")
print()

# Browser engine analysis
print("=== Browser Engine Analysis ===")
def categorize_engine(browser_name):
    if browser_name in ['Chrome', 'Google Chrome', 'Microsoft Edge', 'Brave']:
        return 'Blink'
    elif browser_name in ['Safari', 'Samsung Internet']:
        return 'WebKit'
    elif browser_name == 'Firefox':
        return 'Gecko'
    else:
        return 'Other'

wasm_data['engine'] = wasm_data['browser_name'].apply(categorize_engine)
for engine in wasm_data['engine'].unique():
    if engine != 'Other':
        engine_data = wasm_data[wasm_data['engine'] == engine]
        print(f"{engine}: {engine_data['total_handshake_mean'].mean():.2f}ms (n={len(engine_data)})")
print()

# Device type analysis
print("=== Mobile vs Desktop ===")
mobile_wasm = wasm_data[wasm_data['device_type'] == 'mobile']
desktop_wasm = wasm_data[wasm_data['device_type'] == 'desktop']
print(f"Mobile WASM: {mobile_wasm['total_handshake_mean'].mean():.2f}ms (n={len(mobile_wasm)})")
print(f"Desktop WASM: {desktop_wasm['total_handshake_mean'].mean():.2f}ms (n={len(desktop_wasm)})")
print()

# Check for field vs lab data
print("=== Field vs Lab Data ===")
field_data = df[df['device_model'] != '[LAB]']
lab_data = df[df['device_model'] == '[LAB]']
print(f"Field sessions: {len(field_data)}")
print(f"Lab sessions: {len(lab_data)}")
print()

# WASM capability statistics
print("=== WASM Feature Availability ===")
print(f"SIMD: {wasm_data['wasm_simd'].mean()*100:.1f}%")
print(f"Threads: {wasm_data['wasm_threads'].mean()*100:.1f}%")
print(f"Bulk Memory: {wasm_data['wasm_bulk_memory'].mean()*100:.1f}%")
