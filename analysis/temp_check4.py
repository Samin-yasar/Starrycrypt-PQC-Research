#!/usr/bin/env python3
import pandas as pd

df = pd.read_csv('performance_data/starrycrypt_telemetry_2026-05-05.csv')
is_c87_all = (df['browser_name'] == 'Chrome') & (df['browser_version'].astype(str).str.startswith('87')) & (df['os_name'] == 'macOS')
df_462 = df[~is_c87_all].copy()

wasm_462 = df_462[df_462['implementation'] == 'wasm']

desktop = wasm_462[wasm_462['device_type'] == 'desktop']['total_handshake_mean']
mobile = wasm_462[wasm_462['device_type'] == 'mobile']['total_handshake_mean']

print(f"Desktop WASM Mean: {desktop.mean():.2f} ms")
print(f"Mobile WASM Mean: {mobile.mean():.2f} ms")
