// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title MedicalRecordRegistry
 * @notice Stores medical record metadata on-chain. Record content stays off-chain.
 */
contract MedicalRecordRegistry {
    struct Record {
        uint256 recordId;
        bytes32 recordHash;
        string ipfsCid;
        uint256 doctorId;
        uint256 hospitalId;
        uint256 timestamp;
    }

    mapping(uint256 => Record) private records;

    event RecordRegistered(
        uint256 indexed recordId,
        bytes32 indexed recordHash,
        string ipfsCid,
        uint256 doctorId,
        uint256 hospitalId,
        uint256 timestamp
    );

    event RecordVerified(
        uint256 indexed recordId,
        bytes32 recordHash,
        bool isValid
    );

    error RecordAlreadyExists(uint256 recordId);
    error RecordNotFound(uint256 recordId);
    error InvalidRecordHash();
    error InvalidIpfsCid();

    /**
     * @notice Register metadata for a medical record.
     * @param recordId Off-chain database record ID.
     * @param recordHash SHA-256 hash of the PDF (32 bytes).
     * @param ipfsCid IPFS content identifier from Pinata.
     * @param doctorId ID of the uploading doctor.
     * @param hospitalId Hospital identifier (e.g. 1 = A, 2 = B, 3 = C).
     */
    function registerRecord(
        uint256 recordId,
        bytes32 recordHash,
        string calldata ipfsCid,
        uint256 doctorId,
        uint256 hospitalId
    ) external {
        if (records[recordId].timestamp != 0) {
            revert RecordAlreadyExists(recordId);
        }
        if (recordHash == bytes32(0)) {
            revert InvalidRecordHash();
        }
        if (bytes(ipfsCid).length == 0) {
            revert InvalidIpfsCid();
        }

        uint256 timestamp = block.timestamp;

        records[recordId] = Record({
            recordId: recordId,
            recordHash: recordHash,
            ipfsCid: ipfsCid,
            doctorId: doctorId,
            hospitalId: hospitalId,
            timestamp: timestamp
        });

        emit RecordRegistered(
            recordId,
            recordHash,
            ipfsCid,
            doctorId,
            hospitalId,
            timestamp
        );
    }

    /**
     * @notice Verify that a record hash matches the hash stored on-chain.
     * @param recordId Record to verify.
     * @param recordHash SHA-256 hash to compare.
     * @return isValid True if the record exists and the hash matches.
     */
    function verifyRecord(
        uint256 recordId,
        bytes32 recordHash
    ) external returns (bool isValid) {
        Record storage stored = records[recordId];
        if (stored.timestamp == 0) {
            revert RecordNotFound(recordId);
        }

        isValid = stored.recordHash == recordHash;
        emit RecordVerified(recordId, recordHash, isValid);
        return isValid;
    }

    /**
     * @notice Retrieve on-chain metadata for a record.
     * @param recordId Record to look up.
     */
    function getRecord(
        uint256 recordId
    )
        external
        view
        returns (
            uint256 id,
            bytes32 recordHash,
            string memory ipfsCid,
            uint256 doctorId,
            uint256 hospitalId,
            uint256 timestamp
        )
    {
        Record storage stored = records[recordId];
        if (stored.timestamp == 0) {
            revert RecordNotFound(recordId);
        }

        return (
            stored.recordId,
            stored.recordHash,
            stored.ipfsCid,
            stored.doctorId,
            stored.hospitalId,
            stored.timestamp
        );
    }
}
