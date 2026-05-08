import csv, math
def mean(data): return sum(data)/len(data) if data else 0
def median(data):
    s = sorted(data)
    n = len(s)
    if n==0: return 0
    return s[n//2] if n%2==1 else (s[n//2-1]+s[n//2])/2
def std(data):
    if len(data)<2: return 0
    m = mean(data)
    return math.sqrt(sum((x-m)**2 for x in data)/(len(data)-1))
def ci95(data):
    m = mean(data); s = std(data); margin = 1.96*s/math.sqrt(len(data))
    return (m-margin, m+margin)

rows = []
with open('../performance_data/starrycrypt_telemetry_2026-05-05.csv', 'r') as f:
    for row in csv.DictReader(f):
        rows.append(row)

wasm = [float(r['total_handshake_mean']) for r in rows if r['implementation'] == 'wasm' and not (r['browser_name'] == 'Chrome' and r['browser_version'].startswith('87') and r['os_name'] == 'macOS')]
js = [float(r['total_handshake_mean']) for r in rows if r['implementation'] == 'pure-js']

print(f'WASM: n={len(wasm)}, mean={mean(wasm):.2f}, med={median(wasm):.2f}, std={std(wasm):.2f}, CI: [{ci95(wasm)[0]:.2f}, {ci95(wasm)[1]:.2f}]')
print(f'JS: n={len(js)}, mean={mean(js):.2f}, med={median(js):.2f}, std={std(js):.2f}, CI: [{ci95(js)[0]:.2f}, {ci95(js)[1]:.2f}]')
