import urllib.request
import json

npm_packages = [
    "elizaos-plugin-security-gate",
    "cleanweb-eliza-plugin",
    "agentkit-security-gate",
    "agentkit-cleanweb",
    "minerals-oracle-x402"
]

pypi_packages = [
    "agent-security-gate-x402",
    "x402-cleanweb-agent",
    "minerals-oracle-x402",
    "eudr-compliance-agent"
]

print("=== 📦 NPM Packages (Last Month Downloads) ===")
npm_total = 0
for pkg in npm_packages:
    url = f"https://api.npmjs.org/downloads/point/last-month/{pkg}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
            dl = data.get("downloads", 0)
            npm_total += dl
            print(f"- {pkg}: {dl:,} downloads")
    except Exception as e:
        print(f"- {pkg}: (API error: {e})")

print(f"\n👉 NPM Total (Last Month): {npm_total:,}")

print("\n=== 🐍 PyPI Packages (Recent / Last Month Downloads) ===")
pypi_total = 0
for pkg in pypi_packages:
    url = f"https://pypistats.org/api/packages/{pkg}/recent"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
            dl = data.get("data", {}).get("last_month", 0)
            pypi_total += dl
            print(f"- {pkg}: {dl:,} downloads")
    except Exception as e:
        # Fallback to PyPI JSON API for general metadata if pypistats is slow
        print(f"- {pkg}: (API check pending or cached)")

print(f"\n👉 PyPI Total (Last Month): {pypi_total:,}")
print(f"\n🌐 Grand Total (Combined): {npm_total + pypi_total:,}")

