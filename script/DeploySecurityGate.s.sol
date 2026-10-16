// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "forge-std/Script.sol";
import "../contracts/SecurityGateProtocol.sol";

contract DeploySecurityGate is Script {
    // Base Mainnet Official USDC Address
    address constant BASE_MAINNET_USDC = 0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913;
    // Base Sepolia Testnet Official USDC Address
    address constant BASE_SEPOLIA_USDC = 0x036CbD53842c5426634e7929541eC2318f3dCF7e;

    function run() external {
        // Load deployer private key and destination addresses from environment
        uint256 deployerPrivateKey = vm.envUint("DEPLOYER_PRIVATE_KEY");
        address gateSigner         = vm.envAddress("GATE_SIGNER_ADDRESS");
        address protocolTreasury   = vm.envAddress("PROTOCOL_TREASURY_ADDRESS");
        address insuranceVault     = vm.envAddress("INSURANCE_VAULT_ADDRESS");
        address relayerGasTank     = vm.envAddress("RELAYER_GAS_TANK_ADDRESS");

        // Automatically resolve USDC address based on chain ID
        address usdcAddress = block.chainid == 8453 ? BASE_MAINNET_USDC : BASE_SEPOLIA_USDC;

        console.log("Deploying Security-Gate-x402 Suite on Chain ID:", block.chainid);
        console.log("Using USDC Contract:", usdcAddress);

        vm.startBroadcast(deployerPrivateKey);

        // 1. Universal Escrow & x402 Fee Router deployment (70:20:10 Revenue Split)
        SecurityGateEscrowRouter escrowRouter = new SecurityGateEscrowRouter(
            usdcAddress,
            gateSigner,
            protocolTreasury,
            insuranceVault,
            relayerGasTank
        );

        // 2. Safe{Wallet} On-Chain Guard module deployment
        SecurityGateSafeGuard safeGuard = new SecurityGateSafeGuard(
            gateSigner
        );

        vm.stopBroadcast();

        console.log("==================================================");
        console.log("SecurityGateEscrowRouter deployed at:", address(escrowRouter));
        console.log("SecurityGateSafeGuard deployed at   :", address(safeGuard));
        console.log("Gate Signer configured as           :", gateSigner);
        console.log("==================================================");
    }
}
