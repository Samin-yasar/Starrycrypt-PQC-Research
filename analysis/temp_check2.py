#!/usr/bin/env python3
import pandas as pd

df = pd.read_csv('performance_data/starrycrypt_telemetry_2026-05-05.csv')
total_csv = len(df)
print(f"Total rows in CSV: {total_csv}")

# Let's see the Chrome 87 sessions
c87 = df[(df['browser_name'] == 'Chrome') & (df['browser_version'].astype(str).str.startswith('87')) & (df['os_name'] == 'macOS')]
print(f"Total Chrome 87 sessions: {len(c87)}")
for _, row in c87.iterrows():
    print(f"  - {row['implementation']}, latency: {row['total_handshake_mean']} ms")

print("\n--- If we exclude ONLY WASM Chrome 87 (N=463 policy) ---")
is_c87_wasm = (df['browser_name'] == 'Chrome') & (df['browser_version'].astype(str).str.startswith('87')) & (df['os_name'] == 'macOS') & (df['implementation'] == 'wasm')
df_463 = df[~is_c87_wasm].copy()

wasm_463 = df_463[df_463['implementation'] == 'wasm']['total_handshake_mean']
js_463 = df_463[df_463['implementation'] == 'pure-js']['total_handshake_mean']

print(f"N: {len(df_463)}")
print(f"WASM N: {len(wasm_463)}, Mean: {wasm_463.mean():.2f} ms")
print(f"JS N: {len(js_463)}, Mean: {js_463.mean():.2f} ms")
print(f"Speedup: {js_463.mean() / wasm_463.mean():.2f}x")

print("\n--- If we exclude ALL Chrome 87 (N=462 policy) ---")
is_c87_all = (df['browser_name'] == 'Chrome') & (df['browser_version'].astype(str).str.startswith('87')) & (df['os_name'] == 'macOS')
df_462 = df[~is_c87_all].copy()

wasm_462 = df_462[df_462['implementation'] == 'wasm']['total_handshake_mean']
js_462 = df_462[df_462['implementation'] == 'pure-js']['total_handshake_mean']

print(f"N: {len(df_462)}")
print(f"WASM N: {len(wasm_462)}, Mean: {wasm_462.mean():.2f} ms")
print(f"JS N: {len(js_462)}, Mean: {js_462.mean():.2f} ms")
print(f"Speedup: {js_462.mean() / wasm_462.mean():.2f}x")

print("\n--- Breakdown for N=463 ---")
lab_463 = df_463[df_463['device_model'].astype(str).str.contains(r'\[LAB\]', na=False)]
field_463 = df_463[~df_463['device_model'].astype(str).str.contains(r'\[LAB\]', na=False)]

print(f"Lab N: {len(lab_463)}")
print(f"  WASM: {len(lab_463[lab_463['implementation'] == 'wasm'])}")
print(f"  JS: {len(lab_463[lab_463['implementation'] == 'pure-js'])}")
print(f"Field N: {len(field_463)}")
print(f"  WASM: {len(field_463[field_463['implementation'] == 'wasm'])}")
print(f"  JS: {len(field_463[field_463['implementation'] == 'pure-js'])}")
