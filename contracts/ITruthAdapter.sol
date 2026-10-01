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
        CONSTRUCTION_BUILD,   // 2: 3D Drone LiDAR point-cloud, BIM matching, concrete compressive strength
        EUDR_FOREST,          // 3: EU Deforestation-free satellite polygon, legal tenure, DDS compliance
        CONFLICT_MINERALS     // 4: OECD 3TG & Cobalt supply chain, RMI audited smelters, conflict-free provenance
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

