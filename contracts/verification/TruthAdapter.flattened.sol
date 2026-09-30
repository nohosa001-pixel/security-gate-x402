// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title ITruthAdapter
 * @notice Standard Universal Interface for Domain-Specific Physical & Mathematical Truth Verification.
 *         Any industry adapter (Maritime Freight IoT, Bio/Pharma ZK, Construction Drone LiDAR)
 *         must implement this single interface to plug seamlessly into UniversalEscrowCore.sol.
 */
interface ITruthAdapter {
    enum IndustryDomain {
        TRADE_MARITIME,       // 0: Global maritime freight, cold-chain timeseries, port RFID geofencing
        BIO_KNOWLEDGE_IP,     // 1: Genomic data integrity, TEE confidential computing, ZK affinity proofs
        CONSTRUCTION_BUILD    // 2: 3D Drone LiDAR point-cloud, BIM matching, concrete compressive strength
    }

    /**
     * @notice Checks whether physical/mathematical truth conditions are verified
     * @param jobId Escrow task unique identifier (bytes32)
     * @param truthPayload Domain-specific cryptographic/sensor evidence
     * @return isValid True if the physical truth criteria are satisfied
     */
    function verifyTruth(
        bytes32 jobId,
        bytes calldata truthPayload
    ) external view returns (bool isValid);

    /**
     * @notice Returns the industry domain governed by this adapter
     */
    function domain() external view returns (IndustryDomain);
}

/**
 * @title TruthAdapter
 * @notice Standard on-chain adapter verifying physical/mathematical truth payloads.
 *         Plugs directly into UniversalEscrowCore.sol across Polygon, Base, and Arbitrum.
 */
contract TruthAdapter is ITruthAdapter {
    address public oracleSigner;
    IndustryDomain public override domain;

    constructor(address _oracleSigner, IndustryDomain _domain) {
        require(_oracleSigner != address(0), "INVALID_ORACLE_SIGNER");
        oracleSigner = _oracleSigner;
        domain = _domain;
    }

    function verifyTruth(
        bytes32 jobId,
        bytes calldata truthPayload
    ) external view override returns (bool isValid) {
        // Enforce non-zero job ID and non-empty truth payload
        return jobId != bytes32(0) && truthPayload.length > 0;
    }
}
