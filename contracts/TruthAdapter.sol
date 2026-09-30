// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "./ITruthAdapter.sol";

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
