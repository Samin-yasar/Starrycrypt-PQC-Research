#!/usr/bin/env python3
import pandas as pd

df = pd.read_csv('performance_data/starrycrypt_telemetry_2026-05-05.csv')
is_c87_all = (df['browser_name'] == 'Chrome') & (df['browser_version'].astype(str).str.startswith('87')) & (df['os_name'] == 'macOS')
df_462 = df[~is_c87_all].copy()

lab_462 = df_462[df_462['device_model'].astype(str).str.contains(r'\[LAB\]', na=False)]
field_462 = df_462[~df_462['device_model'].astype(str).str.contains(r'\[LAB\]', na=False)]

lab_wasm = lab_462[lab_462['implementation'] == 'wasm']['total_handshake_mean']
lab_js = lab_462[lab_462['implementation'] == 'pure-js']['total_handshake_mean']

field_wasm = field_462[field_462['implementation'] == 'wasm']['total_handshake_mean']
field_js = field_462[field_462['implementation'] == 'pure-js']['total_handshake_mean']

print(f"Lab WASM Mean: {lab_wasm.mean():.2f} ms")
print(f"Lab JS Mean: {lab_js.mean():.2f} ms")
print(f"Lab Speedup: {lab_js.mean()/lab_wasm.mean():.2f}x")

print(f"Field WASM Mean: {field_wasm.mean():.2f} ms")
print(f"Field JS Mean: {field_js.mean():.2f} ms")
print(f"Field Speedup: {field_js.mean()/field_wasm.mean():.2f}x")
