// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// @title Violation metadata logger for human-reviewed traffic events.
/// @notice Stores hashes and metadata only — no raw media or plate text on-chain.
contract ViolationLogger {
    address public owner;

    struct ViolationRecord {
        bytes32 eventId;
        uint64 timestampUtc;
        bytes32 violationTypeHash;
        bytes32 evidenceHash;
        bytes32 plateHash;
        address recordedBy;
        bool exists;
    }

    mapping(bytes32 => ViolationRecord) private _records;

    event ViolationLogged(
        bytes32 indexed eventId,
        uint64 timestampUtc,
        bytes32 violationTypeHash,
        bytes32 evidenceHash,
        bytes32 plateHash,
        address indexed recordedBy
    );

    error NotOwner();
    error EmptyEventId();
    error DuplicateEvent(bytes32 eventId);

    modifier onlyOwner() {
        if (msg.sender != owner) {
            revert NotOwner();
        }
        _;
    }

    constructor() {
        owner = msg.sender;
    }

    function logViolation(
        bytes32 eventId,
        uint64 timestampUtc,
        bytes32 violationTypeHash,
        bytes32 evidenceHash,
        bytes32 plateHash
    ) external onlyOwner {
        if (eventId == bytes32(0)) {
            revert EmptyEventId();
        }
        if (_records[eventId].exists) {
            revert DuplicateEvent(eventId);
        }
        _records[eventId] = ViolationRecord({
            eventId: eventId,
            timestampUtc: timestampUtc,
            violationTypeHash: violationTypeHash,
            evidenceHash: evidenceHash,
            plateHash: plateHash,
            recordedBy: msg.sender,
            exists: true
        });
        emit ViolationLogged(
            eventId,
            timestampUtc,
            violationTypeHash,
            evidenceHash,
            plateHash,
            msg.sender
        );
    }

    function getViolation(bytes32 eventId)
        external
        view
        returns (
            uint64 timestampUtc,
            bytes32 violationTypeHash,
            bytes32 evidenceHash,
            bytes32 plateHash,
            address recordedBy,
            bool exists
        )
    {
        ViolationRecord memory record = _records[eventId];
        return (
            record.timestampUtc,
            record.violationTypeHash,
            record.evidenceHash,
            record.plateHash,
            record.recordedBy,
            record.exists
        );
    }

    function transferOwnership(address newOwner) external onlyOwner {
        owner = newOwner;
    }
}
