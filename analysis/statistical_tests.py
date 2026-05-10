import csv
import numpy as np
from scipy import stats
import math

def load_data(filepath):
    rows = []
    with open(filepath, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            for key in ['total_handshake_mean']:
                try:
                    row[key] = float(row[key]) if row[key] else 0.0
                except:
                    row[key] = 0.0
            rows.append(row)
    return rows

rows = load_data('performance_data/starrycrypt_telemetry_2026-05-05.csv')

wasm_all = [r['total_handshake_mean'] for r in rows if r['implementation'] == 'wasm']
wasm_no_c87 = [r['total_handshake_mean'] for r in rows if r['implementation'] == 'wasm' and not (r['browser_name'] == 'Chrome' and r['browser_version'].startswith('87') and r['os_name'] == 'macOS')]
js_all = [r['total_handshake_mean'] for r in rows if r['implementation'] == 'pure-js']

# To numpy arrays
w_all = np.array(wasm_all)
w_no_c87 = np.array(wasm_no_c87)
j_all = np.array(js_all)

print(f"WASM (With C87) - n={len(w_all)}, mean={np.mean(w_all):.3f}, std (ddof=1)={np.std(w_all, ddof=1):.3f}")
print(f"WASM (Without C87) - n={len(w_no_c87)}, mean={np.mean(w_no_c87):.3f}, std (ddof=1)={np.std(w_no_c87, ddof=1):.3f}")
print(f"JS (All) - n={len(j_all)}, mean={np.mean(j_all):.3f}, std (ddof=1)={np.std(j_all, ddof=1):.3f}")

# Welch's t-test with Chrome 87
t_stat_with, p_val_with = stats.ttest_ind(w_all, j_all, equal_var=False)
print(f"\n--- With Chrome 87 ---")
print(f"t-statistic: {t_stat_with:.3f}, p-value: {p_val_with:.6f}")

# Welch's t-test without Chrome 87
t_stat_without, p_val_without = stats.ttest_ind(w_no_c87, j_all, equal_var=False)
print(f"--- Without Chrome 87 ---")
print(f"t-statistic: {t_stat_without:.3f}, p-value: {p_val_without:.6e}")

# Cohen's d
def cohen_d(x, y):
    nx = len(x)
    ny = len(y)
    dof = nx + ny - 2
    return (np.mean(x) - np.mean(y)) / math.sqrt(((nx-1)*np.std(x, ddof=1)**2 + (ny-1)*np.std(y, ddof=1)**2) / dof)

d_with = abs(cohen_d(w_all, j_all))
d_without = abs(cohen_d(w_no_c87, j_all))

print(f"\nCohen's d (With C87): {d_with:.3f}")
print(f"Cohen's d (Without C87): {d_without:.3f}")

# Confidence Intervals (95%)
w_no_c87_margin = stats.t.ppf(0.975, len(w_no_c87)-1) * (np.std(w_no_c87, ddof=1) / math.sqrt(len(w_no_c87)))
w_no_c87_ci = (np.mean(w_no_c87) - w_no_c87_margin, np.mean(w_no_c87) + w_no_c87_margin)
print(f"\nWASM (Without C87) 95% CI: [{w_no_c87_ci[0]:.2f}, {w_no_c87_ci[1]:.2f}]")

j_margin = stats.t.ppf(0.975, len(j_all)-1) * (np.std(j_all, ddof=1) / math.sqrt(len(j_all)))
j_ci = (np.mean(j_all) - j_margin, np.mean(j_all) + j_margin)
print(f"JS 95% CI: [{j_ci[0]:.2f}, {j_ci[1]:.2f}]")

