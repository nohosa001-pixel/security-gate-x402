import sys
import json
from web3 import Web3

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

RPC = "https://arb1.arbitrum.io/rpc"
w3 = Web3(Web3.HTTPProvider(RPC))

print("=" * 80)
print(f"🌐 [ARBITRUM ONE ON-CHAIN DEEP CONTRACT STATE & INTERACTION AUDIT]")
print(f"Connected: {w3.is_connected()} | Chain ID: {w3.eth.chain_id} | Block #{w3.eth.block_number:,}")
print("=" * 80)

# 1. SecurityGateConsumer
consumer_abi = [
    {"inputs": [], "name": "oracleSigner", "outputs": [{"type": "address"}], "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "owner", "outputs": [{"type": "address"}], "stateMutability": "view", "type": "function"}
]
c = w3.eth.contract(address="0xdC6Cb774d51681Fcbba0E67Ca677dEc5705aaB35", abi=consumer_abi)
print(f"1. SecurityGateConsumer [0xdC6Cb...]:")
print(f"   - oracleSigner: {c.functions.oracleSigner().call()}")
print(f"   - owner:        {c.functions.owner().call()}")

# 2. SafeSecurityGateGuard
guard_abi = [
    {"inputs": [], "name": "oracleSigner", "outputs": [{"type": "address"}], "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "maxAllowedRiskScore", "outputs": [{"type": "uint8"}], "stateMutability": "view", "type": "function"}
]
guard = w3.eth.contract(address="0x306e69E59E5bCEa769C6CeA76A79AFA8f2A5F408", abi=guard_abi)
print(f"\n2. SafeSecurityGateGuard [0x306e6...]:")
print(f"   - oracleSigner: {guard.functions.oracleSigner().call()}")
print(f"   - maxRiskScore: {guard.functions.maxAllowedRiskScore().call()}")

# 3. AgentCreditOracle
oracle_abi = [
    {"inputs": [], "name": "oracleSigner", "outputs": [{"type": "address"}], "stateMutability": "view", "type": "function"}
]
oracle = w3.eth.contract(address="0x227e1129Ba9B39a50fb9E0802bA13A7F77Debe93", abi=oracle_abi)
print(f"\n3. AgentCreditOracle [0x227e1...]:")
print(f"   - oracleSigner: {oracle.functions.oracleSigner().call()}")

# 4. AgentComplianceRegistry
comp_abi = [
    {"inputs": [], "name": "complianceOracleSigner", "outputs": [{"type": "address"}], "stateMutability": "view", "type": "function"}
]
comp = w3.eth.contract(address="0x821d88Df97F6063a32fDff85FBad9784B9B7292D", abi=comp_abi)
print(f"\n4. AgentComplianceRegistry [0x821d8...]:")
print(f"   - complianceOracleSigner: {comp.functions.complianceOracleSigner().call()}")

# 5. AgentEscrow
escrow_abi = [
    {"inputs": [], "name": "oracleSigner", "outputs": [{"type": "address"}], "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "paymentToken", "outputs": [{"type": "address"}], "stateMutability": "view", "type": "function"}
]
escrow = w3.eth.contract(address="0x99FEd65Cf2D5378182c3481B300124BB1a8Ad278", abi=escrow_abi)
print(f"\n5. AgentEscrow [0x99FEd...]:")
print(f"   - oracleSigner: {escrow.functions.oracleSigner().call()}")
print(f"   - paymentToken: {escrow.functions.paymentToken().call()} (Arbitrum Native USDC)")

# 6. AgentTreasuryVault
vault_abi = [
    {"inputs": [], "name": "oracleSigner", "outputs": [{"type": "address"}], "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "usdcToken", "outputs": [{"type": "address"}], "stateMutability": "view", "type": "function"}
]
vault = w3.eth.contract(address="0xF8e1439F61c9F2d5FdbA382D524FabB35e12ae55", abi=vault_abi)
print(f"\n6. AgentTreasuryVault [0xF8e14...]:")
print(f"   - oracleSigner: {vault.functions.oracleSigner().call()}")
print(f"   - usdcToken:    {vault.functions.usdcToken().call()} (Arbitrum Native USDC)")

# 7. AgentInsurancePool
ins_abi = [
    {"inputs": [], "name": "oracleSigner", "outputs": [{"type": "address"}], "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "usdcToken", "outputs": [{"type": "address"}], "stateMutability": "view", "type": "function"}
]
ins = w3.eth.contract(address="0x90308AedEe6430D11e5214cf9d2F563333D33Ef2", abi=ins_abi)
print(f"\n7. AgentInsurancePool [0x90308...]:")
print(f"   - oracleSigner: {ins.functions.oracleSigner().call()}")
print(f"   - usdcToken:    {ins.functions.usdcToken().call()} (Arbitrum Native USDC)")

# 8. AgentLendingPool
lend_abi = [
    {"inputs": [], "name": "creditOracle", "outputs": [{"type": "address"}], "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "usdcToken", "outputs": [{"type": "address"}], "stateMutability": "view", "type": "function"}
]
lend = w3.eth.contract(address="0x5cC5Afa2a97599d492A3E408Fdd95fD0b520f173", abi=lend_abi)
print(f"\n8. AgentLendingPool [0x5cC5A...]:")
print(f"   - creditOracle: {lend.functions.creditOracle().call()}")
print(f"   - usdcToken:    {lend.functions.usdcToken().call()} (Arbitrum Native USDC)")

# 9. AgentFactoringPool
fact_abi = [
    {"inputs": [], "name": "oracleSigner", "outputs": [{"type": "address"}], "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "usdcToken", "outputs": [{"type": "address"}], "stateMutability": "view", "type": "function"}
]
fact = w3.eth.contract(address="0x6418f408cFf03F862D7691f01fAb00a895E6aB93", abi=fact_abi)
print(f"\n9. AgentFactoringPool [0x6418f...]:")
print(f"   - oracleSigner: {fact.functions.oracleSigner().call()}")
print(f"   - usdcToken:    {fact.functions.usdcToken().call()} (Arbitrum Native USDC)")

print("\n" + "=" * 80)
print("✨ [ALL 9 ARBITRUM CONTRACTS VERIFIED OPERATIONAL & RESPONSIVE]")
print("=" * 80)
