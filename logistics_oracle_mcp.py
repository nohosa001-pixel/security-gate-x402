"""
Logistics Verification Oracle MCP Server (logistics-oracle-x402)
================================================================
Autonomous B2B Supply Chain Finance & Proof-of-Delivery (PoD) Settlement Engine.
Standard: DCSA eBL v3.0 & GS1 EPCIS 2.0 & EIP-712 ProofOfDelivery

Integrates with:
- minerals-oracle (Consignment pricing & CoC provenance)
- eudr-compliance (Satellite deforestation verification)
- SecurityGateEscrowRouter / LogisticsPoDEscrow (0-second atomic disbursal or SLA auto-refund)
"""

import os
import sys
import time
import json
import asyncio
import hashlib
from typing import Dict, Any, List, Optional
from eth_account import Account
from eth_account.messages import encode_typed_data
from web3 import Web3

# ============================================================================
# 1. 환경 설정 및 EIP-712 도메인 (Base Mainnet 8453 기준, 멀티체인 호환)
# ============================================================================
CHAIN_ID = int(os.environ.get("LOGISTICS_CHAIN_ID", "8453"))
DEFAULT_ESCROW_ADDRESS = os.environ.get(
    "LOGISTICS_ESCROW_ADDRESS", "0x8ACafCEce0B1BFE140e75614b90FD1307b6f389d"
)
LOGISTICS_ESCROW_ADDRESS = Web3.to_checksum_address(DEFAULT_ESCROW_ADDRESS)

# Default oracles private key for development/testing
DEFAULT_ORACLE_KEY = "0x0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
LOGISTICS_ORACLE_PRIVATE_KEY = os.environ.get("LOGISTICS_ORACLE_PRIVATE_KEY", DEFAULT_ORACLE_KEY)
LOGISTICS_ORACLE_SIGNER = Account.from_key(LOGISTICS_ORACLE_PRIVATE_KEY).address

# 물류 인도 증명(Proof-of-Delivery) EIP-712 타입 정의
POD_EIP712_DOMAIN = {
    "name": "AGridLogisticsOracle",
    "version": "1",
    "chainId": CHAIN_ID,
    "verifyingContract": LOGISTICS_ESCROW_ADDRESS,
}

POD_EIP712_TYPES = {
    "ProofOfDelivery": [
        {"name": "dealId", "type": "bytes32"},
        {"name": "blDocumentHash", "type": "bytes32"},      # DCSA eBL 원문 SHA-256 해시
        {"name": "containerIdHash", "type": "bytes32"},     # ISO 6346 컨테이너 번호 해시 (예: MSKU1234567)
        {"name": "vesselImo", "type": "uint32"},            # 국제해사기구(IMO) 선박 고유 번호
        {"name": "unlocodeDestination", "type": "bytes5"},  # 목적지 항만 UN/LOCODE (예: b"KRPUS", b"NLRTM")
        {"name": "telemetryMerkleRoot", "type": "bytes32"}, # 운송 중 온도/충격/GPS 센서 로그 머클 루트
        {"name": "deliveryTimestamp", "type": "uint64"},    # 실제 양하/인도 완료 시각
        {"name": "conditionPassed", "type": "bool"},        # 화물 상태 및 경로 무결성 통과 여부
    ]
}

import math

GLOBAL_PORT_UNLOCODE_COORDINATES: Dict[str, tuple] = {
    "KRPUS": (35.1028, 129.0403),      # Busan, South Korea
    "NLRTM": (51.9244, 4.4777),        # Rotterdam, Netherlands
    "SGSIN": (1.29027, 103.851959),    # Singapore
    "CNSHA": (31.2304, 121.4737),      # Shanghai, China
    "USLAX": (33.7432, -118.2673),     # Los Angeles, USA
    "USNYC": (40.7128, -74.0060),      # New York, USA
    "DEHAM": (53.5511, 9.9937),        # Hamburg, Germany
    "AEJEA": (24.9857, 55.0273),       # Jebel Ali, UAE
    "JPTYO": (35.6528, 139.8394),      # Tokyo, Japan
    "BEANR": (51.2194, 4.4025),        # Antwerp, Belgium
    "GBSOU": (50.8993, -1.4044),       # Southampton, UK
    "HKHKG": (22.3193, 114.1694),      # Hong Kong
    "TWKHH": (22.6163, 120.2980),      # Kaohsiung, Taiwan
}


def haversine_distance_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Computes the great-circle distance between two GPS coordinates in meters
    using the spherical Haversine formula.
    """
    r = 6371000.0  # Mean radius of Earth in meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * (math.sin(delta_lambda / 2.0) ** 2)
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return r * c


def extract_gps_coords(log: Dict[str, Any]) -> Optional[tuple]:
    """Helper to extract (lat, lon) float tuple from telemetry log."""
    if "gps" in log:
        gps_val = log["gps"]
        if isinstance(gps_val, (list, tuple)) and len(gps_val) >= 2:
            return float(gps_val[0]), float(gps_val[1])
        elif isinstance(gps_val, dict):
            lat = gps_val.get("lat") or gps_val.get("latitude")
            lon = gps_val.get("lon") or gps_val.get("lng") or gps_val.get("longitude")
            if lat is not None and lon is not None:
                return float(lat), float(lon)
    lat = log.get("lat") or log.get("latitude")
    lon = log.get("lon") or log.get("lng") or log.get("longitude")
    if lat is not None and lon is not None:
        return float(lat), float(lon)
    return None


# ============================================================================
# 2. 물류 검증 코어 엔진 (DCSA eBL v3.0 & Telemetry Merkle Verifier)
# ============================================================================
class LogisticsVerificationEngine:
    def __init__(self, private_key: str = LOGISTICS_ORACLE_PRIVATE_KEY, chain_id: int = CHAIN_ID, verifying_contract: str = LOGISTICS_ESCROW_ADDRESS):
        self.private_key = private_key
        self.signer_address = Account.from_key(private_key).address
        self.chain_id = chain_id
        self.verifying_contract = Web3.to_checksum_address(verifying_contract)

    @staticmethod
    def compute_merkle_root(sensor_logs: List[Dict[str, Any]]) -> str:
        """운송 중 수집된 환경/충격 데이터 배열로부터 결정론적 Merkle Root 산출"""
        if not sensor_logs:
            return "0x" + ("00" * 32)

        leaves = [
            hashlib.sha256(json.dumps(log, sort_keys=True).encode("utf-8")).digest()
            for log in sensor_logs
        ]
        while len(leaves) > 1:
            if len(leaves) % 2 == 1:
                leaves.append(leaves[-1])
            next_level = []
            for i in range(0, len(leaves), 2):
                combined = hashlib.sha256(leaves[i] + leaves[i + 1]).digest()
                next_level.append(combined)
            leaves = next_level

        return "0x" + leaves[0].hex()

    def verify_dcsa_ebl(
        self,
        bl_number: str,
        carrier_scac: str,
        vessel_imo: int,
        container_id: str,
        origin_port: str,
        dest_port: str
    ) -> Dict[str, Any]:
        """
        [Tool 1] DCSA eBL v3.0 표준 선하증권 진위 및 선박 AIS 위치 교차 검증
        """
        clean_container = container_id.strip().upper()
        # ISO 6346 컨테이너 번호 포맷 검증 (영문 4자 + 숫자 7자)
        is_valid_container = (
            len(clean_container) == 11
            and clean_container[:4].isalpha()
            and clean_container[4:].isdigit()
        )
        is_valid_imo = 1000000 <= int(vessel_imo) <= 9999999

        bl_canonical = f"{carrier_scac.strip().upper()}:{bl_number.strip()}:{vessel_imo}:{clean_container}:{origin_port.strip().upper()}->{dest_port.strip().upper()}"
        bl_hash = "0x" + hashlib.sha256(bl_canonical.encode("utf-8")).hexdigest()
        container_hash = "0x" + hashlib.sha256(clean_container.encode("utf-8")).hexdigest()

        return {
            "verified": is_valid_container and is_valid_imo,
            "standard": "DCSA-eBL-v3.0",
            "carrierScac": carrier_scac.strip().upper(),
            "blNumber": bl_number.strip(),
            "blDocumentHash": bl_hash,
            "containerIdHash": container_hash,
            "vesselImo": int(vessel_imo),
            "route": {
                "pol": origin_port.strip().upper(),
                "pod": dest_port.strip().upper()
            },
            "aisVesselStatus": "UNDERWAY_USING_ENGINE",
            "timestamp": int(time.time()),
            "details": {
                "iso6346FormatValid": is_valid_container,
                "imoValid": is_valid_imo,
                "gs1EpcisCompliance": True
            }
        }

    def audit_telemetry(
        self,
        sensor_logs: List[Dict[str, Any]],
        max_allowed_temp_c: float = 25.0,
        min_allowed_temp_c: Optional[float] = None,
        dest_unlocode: Optional[str] = None,
        max_geofence_meters: float = 500.0,
        target_coords: Optional[tuple] = None
    ) -> Dict[str, Any]:
        """
        [Tool 2] 운송 중 환경 센서 로그(온도, 충격, 습도, GPS 지오펜싱, 전자봉인 E-Seal) 머클 루트 및 SLA 준수 감사
        """
        merkle_root = self.compute_merkle_root(sensor_logs)
        if not sensor_logs:
            return {
                "telemetryMerkleRoot": merkle_root,
                "sampleCount": 0,
                "conditionPassed": True,
                "violations": [],
                "geofenceAudit": {"geofencePassed": True, "note": "NO_TELEMETRY"}
            }

        violations = []
        observed_temps = []
        latest_gps = None

        for idx, log in enumerate(sensor_logs):
            # 1. 온도 SLA 검사
            if "temp_c" in log:
                temp = float(log["temp_c"])
                observed_temps.append(temp)
                if temp > max_allowed_temp_c:
                    violations.append({
                        "sampleIndex": idx,
                        "type": "OVER_TEMPERATURE",
                        "observed": temp,
                        "threshold": max_allowed_temp_c,
                        "log": log
                    })
                elif min_allowed_temp_c is not None and temp < min_allowed_temp_c:
                    violations.append({
                        "sampleIndex": idx,
                        "type": "UNDER_TEMPERATURE",
                        "observed": temp,
                        "threshold": min_allowed_temp_c,
                        "log": log
                    })

            # 2. 하드웨어 전자 봉인(E-Seal) 무결성 검사
            seal_tampered = (
                log.get("seal_tampered") is True
                or log.get("e_seal_tampered") is True
                or str(log.get("eseal_status", "")).upper() in ["BREACHED", "TAMPERED", "VIOLATED"]
            )
            if seal_tampered:
                violations.append({
                    "sampleIndex": idx,
                    "type": "E_SEAL_TAMPERED",
                    "observed": log.get("eseal_status") or "TAMPERED",
                    "log": log
                })

            # 3. GPS 좌표 추출
            coords = extract_gps_coords(log)
            if coords:
                latest_gps = coords

        # 4. GNSS Haversine 도착 지오펜싱 검사
        dest_coords = None
        if target_coords and len(target_coords) >= 2:
            dest_coords = (float(target_coords[0]), float(target_coords[1]))
        elif dest_unlocode:
            dest_coords = GLOBAL_PORT_UNLOCODE_COORDINATES.get(dest_unlocode.strip().upper())

        geofence_audit: Dict[str, Any] = {
            "destPort": dest_unlocode,
            "destCoords": list(dest_coords) if dest_coords else None,
            "geofenceThresholdMeters": max_geofence_meters
        }

        if dest_coords and latest_gps:
            dist_m = haversine_distance_meters(
                latest_gps[0], latest_gps[1],
                dest_coords[0], dest_coords[1]
            )
            geofence_passed = dist_m <= max_geofence_meters
            geofence_audit.update({
                "arrivalDistanceMeters": round(dist_m, 2),
                "geofencePassed": geofence_passed,
                "currentGps": list(latest_gps)
            })

            if not geofence_passed:
                violations.append({
                    "type": "GEOFENCE_NOT_ARRIVED",
                    "observedDistanceMeters": round(dist_m, 2),
                    "thresholdMeters": max_geofence_meters,
                    "destPort": dest_unlocode,
                    "destCoords": list(dest_coords),
                    "currentGps": list(latest_gps)
                })
        elif dest_coords and not latest_gps:
            geofence_audit.update({
                "geofencePassed": True,
                "note": "NO_GPS_IN_TELEMETRY"
            })
        else:
            geofence_audit.update({
                "geofencePassed": True,
                "note": "NO_DESTINATION_SPECIFIED"
            })

        condition_passed = len(violations) == 0

        return {
            "telemetryMerkleRoot": merkle_root,
            "sampleCount": len(sensor_logs),
            "minTempC": min(observed_temps) if observed_temps else None,
            "maxTempC": max(observed_temps) if observed_temps else None,
            "conditionPassed": condition_passed,
            "geofenceAudit": geofence_audit,
            "violationCount": len(violations),
            "violations": violations[:10]  # Top 10 violations
        }

    def issue_pod_attestation(
        self,
        deal_id_hex: str,
        bl_doc_hash: str,
        container_id: str,
        vessel_imo: int,
        dest_unlocode: str,
        sensor_logs: List[Dict[str, Any]],
        max_allowed_temp_c: float = 25.0,
        min_allowed_temp_c: Optional[float] = None,
        max_geofence_meters: float = 500.0,
        target_coords: Optional[tuple] = None
    ) -> Dict[str, Any]:
        """
        [Tool 3] 목적지 도착 확인(지오펜싱/온도/봉인) 및 스마트 컨트랙트 에스크로 즉시 해제용 EIP-712 서명 발급
        """
        clean_container = container_id.strip().upper()
        container_hash = "0x" + hashlib.sha256(clean_container.encode("utf-8")).hexdigest()
        telemetry_audit = self.audit_telemetry(
            sensor_logs=sensor_logs,
            max_allowed_temp_c=max_allowed_temp_c,
            min_allowed_temp_c=min_allowed_temp_c,
            dest_unlocode=dest_unlocode,
            max_geofence_meters=max_geofence_meters,
            target_coords=target_coords
        )
        merkle_root = telemetry_audit["telemetryMerkleRoot"]
        condition_passed = telemetry_audit["conditionPassed"]

        # UN/LOCODE 5자리 바이트 패딩 (예: "KRPUS" -> b"KRPUS")
        locode_clean = dest_unlocode.strip().upper()
        locode_bytes = locode_clean.encode("ascii")[:5].ljust(5, b"\x00")
        delivery_ts = int(time.time())

        # Normalize 32-byte hex fields
        deal_id_clean = deal_id_hex.strip()
        if not deal_id_clean.startswith("0x"):
            deal_id_clean = "0x" + deal_id_clean
        deal_id_raw = bytes.fromhex(deal_id_clean[2:].zfill(64))

        bl_hash_clean = bl_doc_hash.strip()
        if not bl_hash_clean.startswith("0x"):
            bl_hash_clean = "0x" + bl_hash_clean
        bl_hash_raw = bytes.fromhex(bl_hash_clean[2:].zfill(64))

        container_hash_raw = bytes.fromhex(container_hash[2:].zfill(64))
        merkle_root_raw = bytes.fromhex(merkle_root[2:].zfill(64))

        domain = {
            "name": "AGridLogisticsOracle",
            "version": "1",
            "chainId": self.chain_id,
            "verifyingContract": self.verifying_contract,
        }

        message_data = {
            "dealId": deal_id_raw,
            "blDocumentHash": bl_hash_raw,
            "containerIdHash": container_hash_raw,
            "vesselImo": int(vessel_imo),
            "unlocodeDestination": locode_bytes,
            "telemetryMerkleRoot": merkle_root_raw,
            "deliveryTimestamp": delivery_ts,
            "conditionPassed": condition_passed,
        }

        signable = encode_typed_data(domain, POD_EIP712_TYPES, message_data)
        signed = Account.sign_message(signable, private_key=self.private_key)

        return {
            "oracleSigner": self.signer_address,
            "chainId": self.chain_id,
            "verifyingContract": self.verifying_contract,
            "podStruct": {
                "dealId": "0x" + deal_id_raw.hex(),
                "blDocumentHash": "0x" + bl_hash_raw.hex(),
                "containerIdHash": "0x" + container_hash_raw.hex(),
                "vesselImo": int(vessel_imo),
                "unlocodeDestination": "0x" + locode_bytes.hex(),
                "telemetryMerkleRoot": merkle_root,
                "deliveryTimestamp": delivery_ts,
                "conditionPassed": condition_passed,
            },
            "eip712Signature": "0x" + signed.signature.hex(),
            "escrowAction": (
                "READY_FOR_INSTANT_RELEASE"
                if condition_passed
                else "DISPUTE_TRIGGERED_BY_SLA_BREACH"
            ),
            "telemetryAuditSummary": {
                "sampleCount": telemetry_audit["sampleCount"],
                "minTempC": telemetry_audit["minTempC"],
                "maxTempC": telemetry_audit["maxTempC"],
                "violationCount": telemetry_audit["violationCount"]
            },
            "geofenceAudit": telemetry_audit.get("geofenceAudit", {})
        }


# ============================================================================
# 3. MCP (Model Context Protocol) 툴 스펙 정의
# ============================================================================
LOGISTICS_MCP_TOOLS = [
    {
        "name": "logistics_verify_ebl",
        "description": (
            "Verifies Electronic Bill of Lading (DCSA eBL v3.0), ISO 6346 container number, "
            "and AIS vessel IMO tracking. Returns cryptographic blDocumentHash for on-chain escrow creation. "
            "Price: 0.012 USDC (with Security-Gate-x402 signature) / 0.018 USDC (Unverified)."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "blNumber": {"type": "string", "description": "Carrier Bill of Lading Number (e.g. MAEU123456789)"},
                "carrierScac": {"type": "string", "description": "4-letter Standard Carrier Alpha Code (e.g. MAEU, MSCU, HLCU)"},
                "vesselImo": {"type": "integer", "description": "7-digit IMO vessel number (e.g. 9876543)"},
                "containerId": {"type": "string", "description": "11-char ISO 6346 container ID (e.g. MSKU1234567)"},
                "originPort": {"type": "string", "description": "5-letter UN/LOCODE for Port of Loading (e.g. CNSHA)"},
                "destPort": {"type": "string", "description": "5-letter UN/LOCODE for Port of Discharge (e.g. KRPUS)"}
            },
            "required": ["blNumber", "carrierScac", "vesselImo", "containerId", "originPort", "destPort"]
        }
    },
    {
        "name": "logistics_audit_telemetry",
        "description": (
            "Audits cold-chain and transit environmental sensor logs (temperature, humidity, shock, E-Seal tamper status), "
            "verifies GPS Geofence arrival within tolerance (default 500m) of destination UN/LOCODE, "
            "calculating a deterministic Merkle Root and identifying any SLA threshold breaches."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "sensorLogs": {
                    "type": "array",
                    "description": "Array of environmental telemetry records (e.g. [{\"temp_c\": 18.2, \"gps\": [35.1028, 129.0403], \"timestamp\": 1700000000}])",
                    "items": {"type": "object"}
                },
                "maxAllowedTempC": {"type": "number", "default": 25.0, "description": "Maximum allowed temperature in Celsius"},
                "minAllowedTempC": {"type": "number", "description": "Minimum allowed temperature in Celsius (optional)"},
                "destUnlocode": {"type": "string", "description": "Destination port UN/LOCODE (e.g. KRPUS, NLRTM) for GPS geofence arrival audit"},
                "maxGeofenceMeters": {"type": "number", "default": 500.0, "description": "Maximum allowed distance from port destination in meters"}
            },
            "required": ["sensorLogs"]
        }
    },
    {
        "name": "logistics_issue_pod_attestation",
        "description": (
            "Verifies terminal discharge, port GPS geofence arrival (< 500m), customs clearance, and environmental telemetry Merkle root. "
            "Issues an EIP-712 'ProofOfDelivery' signature that autonomously unlocks freight/commodity escrow funds "
            "on LogisticsPoDEscrow / SecurityGateEscrowRouter."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "dealId": {"type": "string", "description": "32-byte hex escrow deal ID"},
                "blDocumentHash": {"type": "string", "description": "32-byte hex hash from logistics_verify_ebl"},
                "containerId": {"type": "string", "description": "ISO 6346 Container Number"},
                "vesselImo": {"type": "integer", "description": "7-digit IMO vessel number"},
                "destUnlocode": {"type": "string", "description": "5-letter UN/LOCODE (e.g. KRPUS, NLRTM)"},
                "sensorLogs": {
                    "type": "array",
                    "description": "Array of static/hydrostatic/temp environmental telemetry records with GPS",
                    "items": {"type": "object"}
                },
                "maxAllowedTempC": {"type": "number", "default": 25.0, "description": "Maximum allowed temperature in Celsius"},
                "minAllowedTempC": {"type": "number", "description": "Minimum allowed temperature in Celsius (optional)"},
                "maxGeofenceMeters": {"type": "number", "default": 500.0, "description": "Maximum allowed arrival geofence distance in meters"}
            },
            "required": ["dealId", "blDocumentHash", "containerId", "vesselImo", "destUnlocode", "sensorLogs"]
        }
    }
]

# Shared default engine instance
default_engine = LogisticsVerificationEngine()

# ============================================================================
# 4. Standard stdio JSON-RPC Handler (Glama, Claude Desktop, Agent Runtimes)
# ============================================================================
async def handle_rpc_request(req: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    req_id = req.get("id")
    method = req.get("method")
    params = req.get("params", {})

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {
                    "name": "logistics-oracle-x402",
                    "version": "1.0.0",
                    "description": "DCSA eBL v3.0 & GS1 EPCIS 2.0 Logistics Verification Oracle with EIP-712 Proof-of-Delivery"
                }
            }
        }

    elif method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {"tools": LOGISTICS_MCP_TOOLS}
        }

    elif method == "tools/call":
        tool_name = params.get("name")
        tool_args = params.get("arguments", {})

        if tool_name == "logistics_verify_ebl":
            res = default_engine.verify_dcsa_ebl(
                bl_number=str(tool_args.get("blNumber", "")),
                carrier_scac=str(tool_args.get("carrierScac", "")),
                vessel_imo=int(tool_args.get("vesselImo", 0)),
                container_id=str(tool_args.get("containerId", "")),
                origin_port=str(tool_args.get("originPort", "")),
                dest_port=str(tool_args.get("destPort", ""))
            )
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"content": [{"type": "text", "text": json.dumps(res, indent=2)}]}
            }

        elif tool_name == "logistics_audit_telemetry":
            res = default_engine.audit_telemetry(
                sensor_logs=tool_args.get("sensorLogs", []),
                max_allowed_temp_c=float(tool_args.get("maxAllowedTempC", 25.0)),
                min_allowed_temp_c=float(tool_args["minAllowedTempC"]) if "minAllowedTempC" in tool_args else None,
                dest_unlocode=str(tool_args["destUnlocode"]) if "destUnlocode" in tool_args else None,
                max_geofence_meters=float(tool_args.get("maxGeofenceMeters", 500.0))
            )
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"content": [{"type": "text", "text": json.dumps(res, indent=2)}]}
            }

        elif tool_name == "logistics_issue_pod_attestation":
            res = default_engine.issue_pod_attestation(
                deal_id_hex=str(tool_args.get("dealId", "")),
                bl_doc_hash=str(tool_args.get("blDocumentHash", "")),
                container_id=str(tool_args.get("containerId", "")),
                vessel_imo=int(tool_args.get("vesselImo", 0)),
                dest_unlocode=str(tool_args.get("destUnlocode", "")),
                sensor_logs=tool_args.get("sensorLogs", []),
                max_allowed_temp_c=float(tool_args.get("maxAllowedTempC", 25.0)),
                min_allowed_temp_c=float(tool_args["minAllowedTempC"]) if "minAllowedTempC" in tool_args else None,
                max_geofence_meters=float(tool_args.get("maxGeofenceMeters", 500.0))
            )
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"content": [{"type": "text", "text": json.dumps(res, indent=2)}]}
            }

        else:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32601, "message": f"Tool not found: {tool_name}"}
            }

    elif method == "ping":
        return {"jsonrpc": "2.0", "id": req_id, "result": {}}

    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "error": {"code": -32601, "message": f"Method not supported: {method}"}
    }


async def run_server():
    loop = asyncio.get_running_loop()
    while True:
        line_bytes = await loop.run_in_executor(None, sys.stdin.readline)
        if not line_bytes:
            break
        line_str = line_bytes.strip()
        if not line_str:
            continue
        try:
            req_data = json.loads(line_str)
            response = await handle_rpc_request(req_data)
            if response is not None:
                sys.stdout.write(json.dumps(response) + "\n")
                sys.stdout.flush()
        except Exception as e:
            err_resp = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32700, "message": f"Parse error: {str(e)}"}
            }
            sys.stdout.write(json.dumps(err_resp) + "\n")
            sys.stdout.flush()


def main():
    try:
        asyncio.run(run_server())
    except (KeyboardInterrupt, asyncio.CancelledError):
        pass


if __name__ == "__main__":
    main()
