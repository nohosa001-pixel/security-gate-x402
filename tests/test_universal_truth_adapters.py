"""
Universal Modular Truth Adapters Test Suite.
============================================
Validates 3 Real-World Physical Truth Engines:
1. TradeIoTAdapter: Haversine geofence (<500m), cold-chain invariant (-20°C ± 2°C), RFID tag.
2. BioZkAdapter: Genomic Merkle Root verification, sub-10nM binding affinity (Kd).
3. BuildDroneAdapter: 3D Drone LiDAR BIM volumetric match (>=98.5%), 24 MPa concrete strength.
4. Full E2E integration with UniversalEscrowCore Direct Split Payouts.
"""

import time
import pytest
from eth_account import Account

from app.truth_adapters import trade_iot_adapter, bio_zk_adapter, build_drone_adapter
from scripts.demo_universal_escrow_lifecycle import SimulatedUniversalEscrowCore
from app.onchain_signer import onchain_signer


class TestUniversalTruthAdapters:

    # =========================================================================
    # 1. Maritime Freight IoT Truth Adapter Tests
    # =========================================================================

    def test_trade_iot_adapter_success(self):
        """1.1: Validates compliant container delivery within 500m geofence and perfect cold-chain."""
        job_id = "job_maritime_101"
        # Coordinates: Destination Port of Busan, current vessel position ~150m away
        dest_port = (35.1028, 129.0403)
        vessel_gps = (35.1035, 129.0410)  # ~100m away
        # Constant cold chain between -20.5°C and -19.5°C
        temp_logs = [-20.1, -19.8, -20.4, -19.6, -20.0, -19.9]
        rfid = "RFID-BUSAN-GATE-4402"

        res = trade_iot_adapter.verify_maritime_truth(
            job_id=job_id,
            current_gps=vessel_gps,
            destination_port_gps=dest_port,
            temperature_timeseries_celsius=temp_logs,
            rfid_tag=rfid,
            expected_rfid_tag=rfid
        )

        assert res["is_valid"] is True
        assert res["verdict"] == "PASSED"
        assert res["metrics"]["geofence_passed"] is True
        assert res["metrics"]["distance_to_port_meters"] < 500.0
        assert res["metrics"]["cold_chain_passed"] is True
        assert res["metrics"]["rfid_matched"] is True
        assert res["attestation"]["oracle_signer"] == onchain_signer.signer_address

    def test_trade_iot_adapter_temperature_and_geofence_violations(self):
        """1.2: Fails when cold-chain is broken (-10°C thawed) or vessel is outside 500m."""
        job_id = "job_maritime_fail"
        dest_port = (35.1028, 129.0403)
        vessel_gps_far = (35.2000, 129.2000)  # > 15 km away

        # Case A: Thawing cold-chain violation
        res_thawed = trade_iot_adapter.verify_maritime_truth(
            job_id=job_id,
            current_gps=(35.1030, 129.0405),  # Close
            destination_port_gps=dest_port,
            temperature_timeseries_celsius=[-20.0, -15.2, -10.5, -19.8],  # Thawed above -18°C!
            rfid_tag="TAG1",
            expected_rfid_tag="TAG1"
        )
        assert res_thawed["is_valid"] is False
        assert res_thawed["verdict"] == "FAILED"
        assert res_thawed["metrics"]["cold_chain_passed"] is False

        # Case B: Geofence violation
        res_far = trade_iot_adapter.verify_maritime_truth(
            job_id=job_id,
            current_gps=vessel_gps_far,
            destination_port_gps=dest_port,
            temperature_timeseries_celsius=[-20.0, -20.1, -19.9],
            rfid_tag="TAG1",
            expected_rfid_tag="TAG1"
        )
        assert res_far["is_valid"] is False
        assert res_far["metrics"]["geofence_passed"] is False
        assert res_far["metrics"]["distance_to_port_meters"] > 500.0

    # =========================================================================
    # 2. Bio / Pharma ZK Truth Adapter Tests
    # =========================================================================

    def test_bio_zk_adapter_success(self):
        """2.1: Validates genomic merkle root match and sub-10nM binding affinity."""
        job_id = "job_bio_genomics_201"
        expected_root = "0x" + "f" * 64
        actual_root = "0x" + "f" * 64
        kd_affinity = 3.85  # 3.85 nM is tight nanometer affinity (< 10.0 nM)

        res = bio_zk_adapter.verify_bio_zk_truth(
            job_id=job_id,
            genomic_merkle_root=actual_root,
            expected_merkle_root=expected_root,
            binding_affinity_kd_nm=kd_affinity,
            kd_threshold_nm=10.0,
            zk_proof_hex="0x" + "e" * 64,
            tee_enclave_id="INTEL_SGX_ENCLAVE_V3"
        )

        assert res["is_valid"] is True
        assert res["verdict"] == "PASSED"
        assert res["metrics"]["merkle_root_verified"] is True
        assert res["metrics"]["kd_affinity_passed"] is True
        assert res["metrics"]["binding_affinity_kd_nm"] == 3.85
        assert res["attestation"]["oracle_signer"] == onchain_signer.signer_address

    def test_bio_zk_adapter_weak_affinity_and_corrupt_root_rejected(self):
        """2.2: Rejects weak binding affinity (Kd >= 10nM) or mismatched genomic sequence."""
        job_id = "job_bio_fail"
        expected_root = "0x" + "f" * 64

        # Case A: Weak affinity (Kd = 45.2 nM > 10.0 nM)
        res_weak = bio_zk_adapter.verify_bio_zk_truth(
            job_id=job_id,
            genomic_merkle_root=expected_root,
            expected_merkle_root=expected_root,
            binding_affinity_kd_nm=45.2,
            kd_threshold_nm=10.0
        )
        assert res_weak["is_valid"] is False
        assert res_weak["metrics"]["kd_affinity_passed"] is False

        # Case B: Mismatched Merkle Root (data corruption or IP theft attempt)
        res_corrupt = bio_zk_adapter.verify_bio_zk_truth(
            job_id=job_id,
            genomic_merkle_root="0x" + "1" * 64,
            expected_merkle_root=expected_root,
            binding_affinity_kd_nm=2.1
        )
        assert res_corrupt["is_valid"] is False
        assert res_corrupt["metrics"]["merkle_root_verified"] is False

    # =========================================================================
    # 3. Construction Drone LiDAR & BIM Truth Adapter Tests
    # =========================================================================

    def test_build_drone_adapter_success(self):
        """3.1: Validates drone 3D volumetric match >= 98.5% and concrete strength >= 24 MPa."""
        job_id = "job_construction_301"
        target_bim_vol = 5000.0  # 5,000 m³ of concrete structure
        actual_drone_vol = 4960.0  # 4,960 m³ (99.2% match)
        concrete_samples = [28.5, 30.2, 29.0, 31.4, 27.8]  # All > 24 MPa

        res = build_drone_adapter.verify_build_drone_truth(
            job_id=job_id,
            drone_lidar_volume_m3=actual_drone_vol,
            bim_target_volume_m3=target_bim_vol,
            concrete_strength_samples_mpa=concrete_samples,
            min_volumetric_ratio=0.985,
            min_concrete_strength_mpa=24.0,
            bim_spec_hash="0x" + "d" * 64
        )

        assert res["is_valid"] is True
        assert res["verdict"] == "PASSED"
        assert res["metrics"]["volumetric_passed"] is True
        assert res["metrics"]["volumetric_match_ratio"] >= 0.985
        assert res["metrics"]["concrete_strength_passed"] is True
        assert res["metrics"]["avg_concrete_strength_mpa"] >= 24.0

    def test_build_drone_adapter_incomplete_pour_and_weak_concrete_rejected(self):
        """3.2: Rejects incomplete construction or structurally unsafe concrete."""
        job_id = "job_construction_fail"
        target_vol = 10000.0

        # Case A: Incomplete construction (8,500 m³ / 10,000 m³ = 85.0% < 98.5%)
        res_incomplete = build_drone_adapter.verify_build_drone_truth(
            job_id=job_id,
            drone_lidar_volume_m3=8500.0,
            bim_target_volume_m3=target_vol,
            concrete_strength_samples_mpa=[28.0, 30.0]
        )
        assert res_incomplete["is_valid"] is False
        assert res_incomplete["metrics"]["volumetric_passed"] is False

        # Case B: Structurally weak concrete (16.5 MPa < 24.0 MPa)
        res_weak_concrete = build_drone_adapter.verify_build_drone_truth(
            job_id=job_id,
            drone_lidar_volume_m3=9900.0,  # 99% match
            bim_target_volume_m3=target_vol,
            concrete_strength_samples_mpa=[15.0, 16.5, 17.2]  # Unsafe!
        )
        assert res_weak_concrete["is_valid"] is False
        assert res_weak_concrete["metrics"]["concrete_strength_passed"] is False

    # =========================================================================
    # 4. End-to-End Escrow Direct Settlement with Drone Truth
    # =========================================================================

    def test_e2e_construction_escrow_settlement_with_drone_truth(self):
        """4.1: Executes $5,000,000 Construction Escrow direct settlement via Drone LiDAR Truth."""
        escrow = SimulatedUniversalEscrowCore(
            contract_address="0x5555555555555555555555555555555555555555",
            oracle_signer=onchain_signer.signer_address,
            treasury_address="0x06db5A847F24d0feC5151a01937700E221d55e19"
        )
        payer = Account.create().address
        laborer_lead = Account.create().address
        steel_supplier = Account.create().address
        cement_supplier = Account.create().address

        total_milestone = 5_000_000.0  # $5 Million USD Milestone
        job_id = "job_bridge_milestone_4"

        # 1. Payer locks funds in UniversalEscrowCore
        escrow.deposit_escrow(
            job_id=job_id,
            token="0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359",
            amount_usdc=total_milestone,
            domain_int=2,  # Construction
            truth_hash_requirement="0x" + "a" * 64,
            duration_sec=7200,
            payer=payer
        )

        # 2. Drone LiDAR verification succeeds
        drone_eval = build_drone_adapter.verify_build_drone_truth(
            job_id=job_id,
            drone_lidar_volume_m3=4980.0,
            bim_target_volume_m3=5000.0,
            concrete_strength_samples_mpa=[32.0, 31.5, 33.0]
        )
        assert drone_eval["is_valid"] is True
        attestation = drone_eval["attestation"]

        # 3. Direct Split Payout:
        # $2M to Laborers, $2M to Steel Supplier, $987.5K to Cement Supplier, $12.5K (0.25%) to Treasury
        recipients = [
            {"recipient": laborer_lead, "amount": 2_000_000.0},
            {"recipient": steel_supplier, "amount": 2_000_000.0},
            {"recipient": cement_supplier, "amount": 987_500.0}
        ]

        # Adapter verifier closure
        def verifier_hook(jid, payload):
            return drone_eval["is_valid"]

        settle_res = escrow.execute_settlement_with_proof(
            job_id=job_id,
            recipients=recipients,
            truth_payload=b"drone_lidar_point_cloud_data",
            expires_at=attestation["expiresAt"],
            signature_hex="0xmock_valid_oracle_signature",
            adapter_verifier_fn=verifier_hook
        )

        assert settle_res["status"] == "SETTLED_SUCCESSFULLY"
        assert settle_res["total_disbursed_usdc"] == 4_987_500.0
        assert settle_res["protocol_fee_usdc"] == 12_500.0  # Exactly 0.25% of $5M
        assert escrow.balances[laborer_lead] == 2_000_000.0
        assert escrow.balances[steel_supplier] == 2_000_000.0
        assert escrow.balances[cement_supplier] == 987_500.0
        assert escrow.balances[escrow.treasury] == 12_500.0
        assert escrow.balances[escrow.address] == 0.0  # Zero balance remaining in escrow!
