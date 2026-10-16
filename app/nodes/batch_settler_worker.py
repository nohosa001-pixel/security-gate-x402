"""
Node 8: EIP-3009 On-Chain Batch Settler Daemon Worker
======================================================
Polls accumulated vouchers from Redis and periodically batches them
into Base Mainnet Multicall3 settlement transactions.
"""

import asyncio
import os
import time
from app.x402_batch_middleware import OnchainBatchSettler, X402SessionManager, BATCH_INTERVAL_SECONDS

async def run_batch_daemon():
    print("[*] Starting A.GRID EIP-3009 Multicall3 Batch Settler Daemon...")
    settler = OnchainBatchSettler()
    session_manager = X402SessionManager()

    while True:
        try:
            # Check accumulated vouchers and flush if threshold reached or on interval
            vouchers = await session_manager.pop_settleable_vouchers()
            if vouchers:
                print(f"[Settler] Inspecting {len(vouchers)} pending vouchers...")
                result = await settler.settle_batch_multicall(vouchers)
                if result:
                    print(f"[Settler] Batch settlement executed: {result}")
            await asyncio.sleep(BATCH_INTERVAL_SECONDS)

        except (KeyboardInterrupt, asyncio.CancelledError):
            print("[*] Batch Settler Daemon terminating.")
            break
        except Exception as e:
            print(f"[Settler Error] Exception in settlement loop: {e}")
            await asyncio.sleep(10)

def main():
    try:
        asyncio.run(run_batch_daemon())
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    main()
