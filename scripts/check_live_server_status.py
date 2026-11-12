import urllib.request
import json

BASE = 'https://agent-security-gate-x402-212942243360.asia-northeast3.run.app'

print('=== 1. Health Status ===')
try:
    with urllib.request.urlopen(f'{BASE}/health', timeout=5) as r:
        data = json.loads(r.read().decode())
        uptime = data.get('uptime_seconds', 0)
        print("Status:", data.get('status'))
        print("Version:", data.get('version'))
        print(f"Uptime: {uptime:.1f}s ({uptime/3600:.1f} hours)")
        print("Subsystems:", json.dumps(data.get('subsystems', {}), indent=2))
except Exception as e:
    print('Health err:', e)

print('\n=== 2. PoR Reserves ===')
try:
    with urllib.request.urlopen(f'{BASE}/api/v1/escrow/por', timeout=5) as r:
        d = json.loads(r.read().decode())
        print(f"Reserves Verified: ${d.get('reserves_verified_usdc', 0):,.2f} USDC")
        print("Terms:", d.get('terms'))
        print("Compliance:", d.get('compliance'))
except Exception as e:
    print('PoR err:', e)

print('\n=== 3. Security Metrics ===')
try:
    with urllib.request.urlopen(f'{BASE}/metrics', timeout=5) as r:
        for line in r.read().decode().splitlines():
            if not line.startswith('#') and any(k in line for k in ['rate_limited', 'inspections_total', 'uptime', 'onchain']):
                print(line)
except Exception as e:
    print('Metrics err:', e)

