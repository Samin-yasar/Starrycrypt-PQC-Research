#!/usr/bin/env python3
"""
Comprehensive audit of every numerical claim in paper.tex
against the raw telemetry CSV.
"""
import pandas as pd
import numpy as np

df = pd.read_csv('performance_data/starrycrypt_telemetry_2026-05-03.csv')

# Derived columns
def get_tier(mips):
    if pd.isna(mips) or mips < 150: return 'Budget'
    if mips < 400: return 'Mid-Range'
    return 'Flagship'

df['tier'] = df['baseline_mips'].apply(get_tier)

engine_map = {
    'Google Chrome': 'Blink', 'Chrome': 'Blink', 'Brave': 'Blink',
    'Samsung Internet': 'Blink', 'Microsoft Edge': 'Blink',
    'Android WebView': 'Blink',
    'Safari': 'WebKit',
    'Firefox': 'Gecko',
}
df['engine'] = df['browser_name'].map(engine_map)

wasm = df[df['implementation'] == 'wasm']
js   = df[df['implementation'] == 'pure-js']

print("=" * 70)
print("COMPREHENSIVE DATA AUDIT: paper.tex vs performance_data CSV")
print("=" * 70)

# ── 1. TOTAL SESSIONS ────────────────────────────────────────────────────
print(f"\n[1] Total sessions")
print(f"  Paper claims: N=412")
print(f"  CSV actual:   N={len(df)}")
print(f"  {'✅ MATCH' if len(df) == 412 else '❌ MISMATCH'}")

# ── 2. WASM vs JS counts ─────────────────────────────────────────────────
print(f"\n[2] Implementation counts")
print(f"  Paper: WASM n=215, JS n=197  (in Table II)")
print(f"  CSV:   WASM n={len(wasm)}, JS n={len(js)}")
print(f"  {'✅ MATCH' if len(wasm) == 215 and len(js) == 197 else '❌ MISMATCH'}")

# ── 3. WASM overall mean/median ──────────────────────────────────────────
wm = wasm['total_handshake_mean'].mean()
wmed = wasm['total_handshake_mean'].median()
print(f"\n[3] WASM overall")
print(f"  Paper: mean=4.15 ms, median=1.28 ms")
print(f"  CSV:   mean={wm:.2f} ms, median={wmed:.2f} ms")
print(f"  {'✅ MATCH' if abs(wm - 4.15) < 0.01 and abs(wmed - 1.28) < 0.01 else '❌ MISMATCH'}")

# ── 4. JS overall mean/median ────────────────────────────────────────────
jm = js['total_handshake_mean'].mean()
jmed = js['total_handshake_mean'].median()
print(f"\n[4] Pure JS overall")
print(f"  Paper: mean=7.77 ms, median=4.38 ms")
print(f"  CSV:   mean={jm:.2f} ms, median={jmed:.2f} ms")
print(f"  {'✅ MATCH' if abs(jm - 7.77) < 0.01 and abs(jmed - 4.38) < 0.01 else '❌ MISMATCH'}")

# ── 5. Speedup ────────────────────────────────────────────────────────────
speedup = jm / wm
print(f"\n[5] Overall speedup")
print(f"  Paper: 1.9x")
print(f"  CSV:   {speedup:.1f}x")
print(f"  {'✅ MATCH' if abs(speedup - 1.9) < 0.1 else '❌ MISMATCH'}")

# ── 6. SIMD impact ────────────────────────────────────────────────────────
wasm_simd = wasm[wasm['wasm_simd'] == True]
wasm_no_simd = wasm[wasm['wasm_simd'] == False]
sm = wasm_simd['total_handshake_mean'].mean()
smed = wasm_simd['total_handshake_mean'].median()
nsm = wasm_no_simd['total_handshake_mean'].mean()
nsmed = wasm_no_simd['total_handshake_mean'].median()
print(f"\n[6] WASM + SIMD")
print(f"  Paper: mean=2.36, median=1.22, n=208")
print(f"  CSV:   mean={sm:.2f}, median={smed:.2f}, n={len(wasm_simd)}")
print(f"  {'✅ MATCH' if abs(sm - 2.36) < 0.01 and len(wasm_simd) == 208 else '❌ MISMATCH'}")

print(f"\n[7] WASM - SIMD")
print(f"  Paper: mean=57.31, median=14.42, n=7")
print(f"  CSV:   mean={nsm:.2f}, median={nsmed:.2f}, n={len(wasm_no_simd)}")
print(f"  {'✅ MATCH' if abs(nsm - 57.31) < 0.01 and len(wasm_no_simd) == 7 else '❌ MISMATCH'}")

# ── 7. SIMD-to-nonSIMD ratio ─────────────────────────────────────────────
ratio = nsm / sm
print(f"\n[8] SIMD/non-SIMD ratio")
print(f"  Paper: 24x")
print(f"  CSV:   {ratio:.0f}x")
print(f"  {'✅ MATCH' if abs(ratio - 24) < 1 else '❌ MISMATCH'}")

# ── 8. Per-phase means ───────────────────────────────────────────────────
print(f"\n[9] Per-phase means (WASM)")
for col, name, paper_val in [
    ('mlkem_keygen_mean', 'KeyGen', 0.15),
    ('mlkem_encaps_mean', 'Encaps', 0.16),
    ('mlkem_decaps_mean', 'Decaps', 0.21)]:
    v = wasm[col].mean()
    print(f"  {name}: paper={paper_val:.2f}, csv={v:.2f} {'✅' if abs(v - paper_val) < 0.02 else '❌'}")

print(f"\n[10] Per-phase means (JS)")
for col, name, paper_val in [
    ('mlkem_keygen_mean', 'KeyGen', 1.11),
    ('mlkem_encaps_mean', 'Encaps', 1.32),
    ('mlkem_decaps_mean', 'Decaps', 1.65)]:
    v = js[col].mean()
    print(f"  {name}: paper={paper_val:.2f}, csv={v:.2f} {'✅' if abs(v - paper_val) < 0.02 else '❌'}")

# ── 9. Device tiers ──────────────────────────────────────────────────────
print(f"\n[11] Device tier counts (all implementations)")
for t, paper_n in [('Budget', 71), ('Mid-Range', 114), ('Flagship', 30)]:
    n = len(df[df['tier'] == t])
    # Paper says n= for device tiers, but doesn't specify if WASM-only or total
    # Line 230: "Budget (<150, n=71), Mid-Range (150–400, n=114), Flagship (≥400, n=30)"
    # This sums to 215, which is the WASM count. Let me check both.
    n_wasm = len(wasm[wasm['tier'] == t])
    print(f"  {t}: paper n={paper_n}, csv_total={n}, csv_wasm={n_wasm}")

# Check if paper means match WASM-only tiers
print(f"\n[12] Device tier WASM means")
for t, paper_mean in [('Budget', 2.96), ('Mid-Range', 5.04)]:
    sub = wasm[wasm['tier'] == t]
    v = sub['total_handshake_mean'].mean()
    print(f"  {t}: paper={paper_mean:.2f}, csv={v:.2f} {'✅' if abs(v - paper_mean) < 0.05 else '❌'}")

# ── 10. Feature support percentages ──────────────────────────────────────
print(f"\n[13] Feature support")
for col, name, paper_pct in [
    ('wasm_simd', 'SIMD', 96.8),
    ('wasm_threads', 'Threads', 91.5),
    ('wasm_bulk_memory', 'Bulk Memory', 100.0)]:
    pct = df[col].mean() * 100
    print(f"  {name}: paper={paper_pct}%, csv={pct:.1f}% {'✅' if abs(pct - paper_pct) < 0.1 else '❌'}")

# ── 11. Browser engine means ─────────────────────────────────────────────
print(f"\n[14] Browser engine WASM means")
for e, paper_mean, paper_n in [('WebKit', 0.59, 34), ('Blink', 4.77, 155), ('Gecko', 8.33, 13)]:
    sub = wasm[wasm['engine'] == e]
    v = sub['total_handshake_mean'].mean()
    print(f"  {e}: paper mean={paper_mean}, n={paper_n} | csv mean={v:.2f}, n={len(sub)} {'✅' if abs(v - paper_mean) < 0.05 and len(sub) == paper_n else '❌'}")

# ── 12. Mobile vs Desktop ────────────────────────────────────────────────
print(f"\n[15] Mobile vs Desktop (WASM)")
for d, paper_mean, paper_n in [('mobile', 2.34, 149), ('desktop', 9.01, 60)]:
    sub = wasm[wasm['device_type'] == d]
    v = sub['total_handshake_mean'].mean()
    print(f"  {d}: paper mean={paper_mean}, n={paper_n} | csv mean={v:.2f}, n={len(sub)} {'✅' if abs(v - paper_mean) < 0.05 and len(sub) == paper_n else '❌'}")

# ── 13. Dataset composition table counts ─────────────────────────────────
# Paper says lab: WASM=134, JS=134; field: WASM=81, JS=63
# We can't distinguish lab/field from CSV, but totals must add up
print(f"\n[16] Dataset composition check")
print(f"  Paper: Lab WASM=134 + Field WASM=81 = 215 total WASM")
print(f"  CSV:   Total WASM = {len(wasm)}")
print(f"  Paper: Lab JS=134 + Field JS=63 = 197 total JS")
print(f"  CSV:   Total JS = {len(js)}")
print(f"  Paper: Lab=268 + Field=144 = 412")
print(f"  CSV:   Total = {len(df)}")
lab_wasm = 134; field_wasm = 81; lab_js = 134; field_js = 63
total_check = (lab_wasm + field_wasm == len(wasm)) and (lab_js + field_js == len(js))
print(f"  {'✅ SUMS CORRECT' if total_check else '❌ SUMS DO NOT MATCH'}")

# ── 14. WASM+SIMD speedup vs JS ──────────────────────────────────────────
simd_speedup = jm / sm
print(f"\n[17] WASM+SIMD speedup over JS")
print(f"  Paper: 3.3x (Table II)")
print(f"  CSV:   {simd_speedup:.1f}x")
print(f"  {'✅ MATCH' if abs(simd_speedup - 3.3) < 0.1 else '❌ MISMATCH'}")

# ── 15. Tier n values — paper says these in parentheses ──────────────────
print(f"\n[18] Tier n-values context check")
# Line 230 says Budget n=71, Mid n=114, Flagship n=30 — these sum to 215
tier_sum = sum(len(wasm[wasm['tier'] == t]) for t in ['Budget', 'Mid-Range', 'Flagship'])
print(f"  Paper tier totals: 71+114+30 = 215")
print(f"  CSV WASM tier total: {tier_sum}")
all_tier_total = sum(len(df[df['tier'] == t]) for t in ['Budget', 'Mid-Range', 'Flagship'])
print(f"  CSV ALL tier total: {all_tier_total}")
# Check: does 71+114+30 = 215 (WASM count)?
for t, paper_n in [('Budget', 71), ('Mid-Range', 114), ('Flagship', 30)]:
    n_wasm = len(wasm[wasm['tier'] == t])
    n_all = len(df[df['tier'] == t])
    print(f"    {t}: WASM={n_wasm}, ALL={n_all}, paper={paper_n}")

# ── 16. Mobile+Desktop WASM = total WASM ─────────────────────────────────
mob = len(wasm[wasm['device_type'] == 'mobile'])
desk = len(wasm[wasm['device_type'] == 'desktop'])
print(f"\n[19] Mobile+Desktop sanity")
print(f"  Paper: mobile n=149 + desktop n=60 = 209")
print(f"  CSV:   mobile n={mob} + desktop n={desk} = {mob+desk}")
print(f"  Total WASM: {len(wasm)}")
if mob + desk != len(wasm):
    missing = len(wasm) - mob - desk
    other_types = wasm[~wasm['device_type'].isin(['mobile', 'desktop'])]['device_type'].value_counts()
    print(f"  ⚠️  {missing} sessions have other device_type: {dict(other_types)}")

# ── SUMMARY ──────────────────────────────────────────────────────────────
print("\n" + "=" * 70)
print("AUDIT COMPLETE")
print("=" * 70)
