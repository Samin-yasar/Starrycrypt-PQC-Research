import csv, math
def mean(data): return sum(data)/len(data) if data else 0
def std(data):
    if len(data)<2: return 0
    m = mean(data)
    return math.sqrt(sum((x-m)**2 for x in data)/(len(data)-1))

rows = []
with open('../performance_data/starrycrypt_telemetry_2026-05-05.csv', 'r') as f:
    for row in csv.DictReader(f):
        rows.append(row)

wasm_all = [float(r['total_handshake_mean']) for r in rows if r['implementation'] == 'wasm']
wasm_no_c87 = [float(r['total_handshake_mean']) for r in rows if r['implementation'] == 'wasm' and not (r['browser_name'] == 'Chrome' and r['browser_version'].startswith('87') and r['os_name'] == 'macOS')]

print(f'WASM all: std={std(wasm_all):.2f}')
print(f'WASM no C87: std={std(wasm_no_c87):.2f}')
