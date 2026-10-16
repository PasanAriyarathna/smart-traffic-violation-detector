"""Ethereum client for logging human-reviewed violation metadata."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

VIOLATION_LOGGER_ABI: list[dict[str, Any]] = [
    {
        "inputs": [
            {"internalType": "bytes32", "name": "eventId", "type": "bytes32"},
            {"internalType": "uint64", "name": "timestampUtc", "type": "uint64"},
            {"internalType": "bytes32", "name": "violationTypeHash", "type": "bytes32"},
            {"internalType": "bytes32", "name": "evidenceHash", "type": "bytes32"},
            {"internalType": "bytes32", "name": "plateHash", "type": "bytes32"},
        ],
        "name": "logViolation",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "internalType": "bytes32", "name": "eventId", "type": "bytes32"},
            {"indexed": False, "internalType": "uint64", "name": "timestampUtc", "type": "uint64"},
            {"indexed": False, "internalType": "bytes32", "name": "violationTypeHash", "type": "bytes32"},
            {"indexed": False, "internalType": "bytes32", "name": "evidenceHash", "type": "bytes32"},
            {"indexed": False, "internalType": "bytes32", "name": "plateHash", "type": "bytes32"},
            {"indexed": True, "internalType": "address", "name": "recordedBy", "type": "address"},
        ],
        "name": "ViolationLogged",
        "type": "event",
    },
]


def uuid_to_bytes32(event_uuid: str) -> bytes:
    from hashlib import sha256

    return sha256(event_uuid.encode("utf-8")).digest()


def text_to_bytes32(text: str) -> bytes:
    from hashlib import sha256

    return sha256(text.encode("utf-8")).digest()


def hex_to_bytes32(hex_digest: str) -> bytes:
    value = hex_digest.removeprefix("0x")
    if len(value) != 64:
        raise ValueError("Expected a 32-byte hex digest")
    return bytes.fromhex(value)


@dataclass(frozen=True)
class ChainLogResult:
    transaction_hash: str
    latency_seconds: float
    block_number: int | None


class ViolationChainClient:
    def __init__(
        self,
        rpc_url: str,
        private_key: str,
        contract_address: str,
        *,
        abi: list[dict[str, Any]] | None = None,
    ) -> None:
        try:
            from web3 import Web3
        except ImportError as exc:
            raise RuntimeError(
                "web3 is not installed. Install backend requirements from requirements-backend.txt"
            ) from exc

        self._web3 = Web3(Web3.HTTPProvider(rpc_url))
        if not self._web3.is_connected():
            raise RuntimeError(f"Could not connect to RPC endpoint: {rpc_url}")
        self._account = self._web3.eth.account.from_key(private_key)
        self._contract = self._web3.eth.contract(
            address=self._web3.to_checksum_address(contract_address),
            abi=abi or VIOLATION_LOGGER_ABI,
        )

    def log_reviewed_violation(
        self,
        *,
        event_uuid: str,
        timestamp_utc: int,
        candidate_type: str,
        evidence_hash_hex: str,
        plate_hash_hex: str,
        gas_limit: int = 300_000,
    ) -> ChainLogResult:
        started = time.perf_counter()
        event_id = uuid_to_bytes32(event_uuid)
        violation_type_hash = text_to_bytes32(candidate_type)
        evidence_hash = hex_to_bytes32(evidence_hash_hex)
        plate_hash = hex_to_bytes32(plate_hash_hex)

        nonce = self._web3.eth.get_transaction_count(self._account.address)
        chain_id = self._web3.eth.chain_id
        transaction = self._contract.functions.logViolation(
            event_id,
            timestamp_utc,
            violation_type_hash,
            evidence_hash,
            plate_hash,
        ).build_transaction(
            {
                "from": self._account.address,
                "nonce": nonce,
                "chainId": chain_id,
                "gas": gas_limit,
            }
        )
        signed = self._web3.eth.account.sign_transaction(transaction, private_key=self._account.key)
        tx_hash = self._web3.eth.send_raw_transaction(signed.raw_transaction)
        receipt = self._web3.eth.wait_for_transaction_receipt(tx_hash)
        latency = time.perf_counter() - started
        return ChainLogResult(
            transaction_hash=tx_hash.hex(),
            latency_seconds=latency,
            block_number=int(receipt.blockNumber) if receipt else None,
        )


def load_contract_address(path: Path) -> str:
    payload = json.loads(path.read_text(encoding="utf-8"))
    address = payload.get("address")
    if not address:
        raise ValueError(f"Missing contract address in {path}")
    return str(address)
