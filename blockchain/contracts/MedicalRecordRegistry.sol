// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title MedicalRecordRegistry
 * @notice Stores immutable medical-record references on-chain.
 *
 * The actual medical record is stored off-chain in IPFS.
 * The SHA-256 hash of the record is used as its global identifier.
 */
contract MedicalRecordRegistry {
    struct Record {
        bytes32 recordHash;
        string ipfsCid;
        uint256 doctorId;
        uint256 hospitalId;
        uint256 timestamp;
    }

    /**
     * recordHash => Record metadata
     *
     * We intentionally do NOT use a central database ID here.
     * The record's cryptographic hash is its identity.
     */
    mapping(bytes32 => Record) private records;

    event RecordRegistered(
        bytes32 indexed recordHash,
        string ipfsCid,
        uint256 doctorId,
        uint256 hospitalId,
        uint256 timestamp
    );

    error RecordAlreadyExists(bytes32 recordHash);
    error RecordNotFound(bytes32 recordHash);
    error InvalidRecordHash();
    error InvalidIpfsCid();

    /**
     * @notice Register a medical record on-chain.
     *
     * @param recordHash SHA-256 hash of the medical record.
     * @param ipfsCid CID of the corresponding record stored in IPFS.
     * @param doctorId ID of the doctor who registered the record.
     * @param hospitalId Numeric identifier of the doctor's hospital.
     */
    function registerRecord(
        bytes32 recordHash,
        string calldata ipfsCid,
        uint256 doctorId,
        uint256 hospitalId
    ) external {
        if (recordHash == bytes32(0)) {
            revert InvalidRecordHash();
        }

        if (bytes(ipfsCid).length == 0) {
            revert InvalidIpfsCid();
        }

        if (records[recordHash].timestamp != 0) {
            revert RecordAlreadyExists(recordHash);
        }

        uint256 timestamp = block.timestamp;

        records[recordHash] = Record({
            recordHash: recordHash,
            ipfsCid: ipfsCid,
            doctorId: doctorId,
            hospitalId: hospitalId,
            timestamp: timestamp
        });

        emit RecordRegistered(
            recordHash,
            ipfsCid,
            doctorId,
            hospitalId,
            timestamp
        );
    }

    /**
     * @notice Return whether a record exists on-chain.
     *
     * @param recordHash SHA-256 hash of the record.
     */
    function verifyRecord(
        bytes32 recordHash
    ) external view returns (bool) {
        return records[recordHash].timestamp != 0;
    }

    /**
     * @notice Retrieve metadata for a record.
     *
     * @param recordHash SHA-256 hash identifying the record.
     */
    function getRecord(
        bytes32 recordHash
    )
        external
        view
        returns (
            bytes32 hash,
            string memory ipfsCid,
            uint256 doctorId,
            uint256 hospitalId,
            uint256 timestamp
        )
    {
        Record storage stored = records[recordHash];

        if (stored.timestamp == 0) {
            revert RecordNotFound(recordHash);
        }

        return (
            stored.recordHash,
            stored.ipfsCid,
            stored.doctorId,
            stored.hospitalId,
            stored.timestamp
        );
    }
}