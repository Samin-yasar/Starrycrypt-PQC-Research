#!/usr/bin/env python3
import pandas as pd
import numpy as np
from scipy import stats

df = pd.read_csv('performance_data/starrycrypt_telemetry_2026-05-05.csv')

print('=== VERIFICATION: Statistics from Data ===')
print()

wasm = df[df['implementation'] == 'wasm']['total_handshake_mean'].dropna()
js = df[df['implementation'] == 'pure-js']['total_handshake_mean'].dropna()

print('WASM Statistics:')
print(f'  n: {len(wasm)}')
print(f'  Mean: {wasm.mean():.2f} ms')
print(f'  Median: {wasm.median():.2f} ms')
print(f'  Std: {wasm.std():.2f} ms')
print()

print('JS Statistics:')
print(f'  n: {len(js)}')
print(f'  Mean: {js.mean():.2f} ms')
print(f'  Median: {js.median():.2f} ms')
print(f'  Std: {js.std():.2f} ms')
print()

print(f'Speedup (JS/WASM): {js.mean() / wasm.mean():.2f}x')
print()

wasm_full = df[df['implementation'] == 'wasm']
wasm_simd = wasm_full[wasm_full['wasm_simd'] == True]['total_handshake_mean'].dropna()
wasm_legacy = wasm_full[wasm_full['wasm_simd'] == False]['total_handshake_mean'].dropna()

print('WASM by SIMD capability:')
print(f'  SIMD-capable n: {len(wasm_simd)}')
print(f'  SIMD-capable mean: {wasm_simd.mean():.2f} ms')
print(f'  Legacy n: {len(wasm_legacy)}')
print(f'  Legacy mean: {wasm_legacy.mean():.2f} ms')
if len(wasm_legacy) > 0 and wasm_legacy.mean() > 0:
    print(f'  Legacy/SIMD ratio: {wasm_legacy.mean() / wasm_simd.mean():.1f}x')
print()

print('Per-phase WASM means:')
print(f'  KeyGen: {wasm_full["mlkem_keygen_mean"].mean():.3f} ms')
print(f'  Encaps: {wasm_full["mlkem_encaps_mean"].mean():.3f} ms')
print(f'  Decaps: {wasm_full["mlkem_decaps_mean"].mean():.3f} ms')
print()

js_full = df[df['implementation'] == 'pure-js']
print('Per-phase JS means:')
print(f'  KeyGen: {js_full["mlkem_keygen_mean"].mean():.3f} ms')
print(f'  Encaps: {js_full["mlkem_encaps_mean"].mean():.3f} ms')
print(f'  Decaps: {js_full["mlkem_decaps_mean"].mean():.3f} ms')
print()

engine_map = {'Safari': 'WebKit', 'Chrome': 'Blink', 'Firefox': 'Gecko', 'Google Chrome': 'Blink'}
wasm_copy = wasm_full.copy()
wasm_copy['engine'] = wasm_copy['browser_name'].map(engine_map)
print('Browser engine means (WASM):')
for engine in ['WebKit', 'Blink', 'Gecko']:
    data = wasm_copy[wasm_copy['engine'] == engine]['total_handshake_mean'].dropna()
    print(f'  {engine}: {data.mean():.2f} ms (n={len(data)})')
print()

mobile = wasm_full[wasm_full['device_type'] == 'mobile']['total_handshake_mean'].dropna()
desktop = wasm_full[wasm_full['device_type'] == 'desktop']['total_handshake_mean'].dropna()
print('Mobile vs Desktop (WASM):')
print(f'  Mobile: {mobile.mean():.2f} ms (n={len(mobile)})')
print(f'  Desktop: {desktop.mean():.2f} ms (n={len(desktop)})')
print()

def get_tier(mips):
    if pd.isna(mips) or mips < 150: return 'Budget'
    if mips < 400: return 'Mid-Range'
    return 'Flagship'

wasm_copy['tier'] = wasm_copy['baseline_mips'].apply(get_tier)
print('WASM by device tier:')
for tier in ['Budget', 'Mid-Range', 'Flagship']:
    data = wasm_copy[wasm_copy['tier'] == tier]['total_handshake_mean'].dropna()
    print(f'  {tier}: {data.mean():.2f} ms (n={len(data)})')
print()

print('=== CLAIMS IN PAPER vs DATA ===')
print()
print('ABSTRACT:')
print(f'  Claim: 1.76x speedup (4.68ms vs 8.25ms)')
print(f'  Data:  {js.mean()/wasm.mean():.2f}x ({wasm.mean():.2f}ms vs {js.mean():.2f}ms)')
print()

print('SIMD-capable browsers:')
print(f'  Claim: 3.36ms')
print(f'  Data:  {wasm_simd.mean():.2f}ms')
print()

print('Legacy browsers:')
print(f'  Claim: 39.6ms (12x penalty)')
print(f'  Data:  {wasm_legacy.mean():.2f}ms ({wasm_legacy.mean()/wasm_simd.mean():.1f}x penalty)')
