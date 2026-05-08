import pandas as pd

df = pd.read_csv('performance_data/starrycrypt_telemetry_2026-05-03.csv')

is_lab = df['device_model'].fillna('').str.contains(r'\[LAB\]')
lab = df[is_lab]
field = df[~is_lab]

print('=== TOTAL ===')
print(f'Total: {len(df)}')
print(f'Lab/Synthetic: {len(lab)}')
print(f'Field/Real: {len(field)}')
print()

print('=== LAB BREAKDOWN ===')
print('Implementations:', lab['implementation'].value_counts().to_dict())
print('Device types:', lab['device_type'].value_counts().to_dict())
print('Browsers:', lab['browser_name'].value_counts().to_dict())
print()

print('=== FIELD BREAKDOWN ===')
print('Implementations:', field['implementation'].value_counts().to_dict())
print('Device types:', field['device_type'].value_counts().to_dict())
print('Browsers:', field['browser_name'].value_counts().to_dict())
print('OS:', field['os_name'].value_counts().to_dict())
print()

print('=== LATENCY STATS (WASM vs JS) ===')
wasm = df[df['implementation'] == 'wasm']['total_handshake_mean']
js = df[df['implementation'] == 'pure-js']['total_handshake_mean']
print(f'WASM mean={wasm.mean():.3f} median={wasm.median():.3f} min={wasm.min():.3f} max={wasm.max():.3f}')
print(f'JS mean={js.mean():.3f} median={js.median():.3f} min={js.min():.3f} max={js.max():.3f}')
print(f'Speedup mean={js.mean()/wasm.mean():.1f}x')
print()

print('=== WASM by TIER ===')
wasm_all = df[df['implementation'] == 'wasm']
for tier, mips_low, mips_high in [('Budget', 0, 150), ('Mid-Range', 150, 400), ('Flagship', 400, 999999)]:
    sub = wasm_all[(wasm_all['baseline_mips'] >= mips_low) & (wasm_all['baseline_mips'] < mips_high)]
    if len(sub) > 0:
        print(f'{tier}: n={len(sub)} mean={sub["total_handshake_mean"].mean():.3f}ms')
    else:
        print(f'{tier}: n=0')
print()

print('=== WASM by RAM ===')
for ram in sorted(wasm_all['ram_gib'].dropna().unique()):
    sub = wasm_all[wasm_all['ram_gib'] == ram]
    print(f'{int(ram)} GiB: n={len(sub)} mean={sub["total_handshake_mean"].mean():.3f}ms')
print()

print('=== WASM by ENGINE ===')
engine_map = {
    'Google Chrome': 'Blink', 'Chrome': 'Blink', 'Brave': 'Blink',
    'Samsung Internet': 'Blink', 'Microsoft Edge': 'Blink',
    'Android WebView': 'Blink',
    'Safari': 'WebKit',
    'Firefox': 'Gecko',
}
wasm_copy = wasm_all.copy()
wasm_copy['engine'] = wasm_copy['browser_name'].map(engine_map)
for engine in ['Blink', 'WebKit', 'Gecko']:
    sub = wasm_copy[wasm_copy['engine'] == engine]
    if len(sub) > 0:
        print(f'{engine}: n={len(sub)} mean={sub["total_handshake_mean"].mean():.3f}ms median={sub["total_handshake_mean"].median():.3f}ms')
print()

print('=== WASM SIMD IMPACT ===')
wasm_simd_yes = wasm_all[wasm_all['wasm_simd'] == True]['total_handshake_mean']
wasm_simd_no = wasm_all[wasm_all['wasm_simd'] == False]['total_handshake_mean']
print(f'SIMD=yes: n={len(wasm_simd_yes)} mean={wasm_simd_yes.mean():.3f}ms')
print(f'SIMD=no: n={len(wasm_simd_no)} mean={wasm_simd_no.mean():.3f}ms')
print()

print('=== MOBILE vs DESKTOP ===')
for impl in ['wasm', 'pure-js']:
    for dt in ['mobile', 'desktop']:
        sub = df[(df['implementation'] == impl) & (df['device_type'] == dt)]
        if len(sub) > 0:
            print(f'{impl} {dt}: n={len(sub)} mean={sub["total_handshake_mean"].mean():.3f}ms')
print()

print('=== FIELD GEO ===')
print('Platform:', field['platform'].value_counts().to_dict())
print('Field RAM:', field['ram_gib'].value_counts().to_dict())
print('Field device_type:', field['device_type'].value_counts().to_dict())
