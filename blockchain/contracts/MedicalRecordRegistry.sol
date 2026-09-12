// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title MedicalRecordRegistry
 * @notice Wallet-based registry for immutable IPFS medical-record references.
 *
 * No patient ID, patient name, doctor database ID, or hospital database ID is
 * stored. Clinician identity is represented only by an Ethereum wallet.
 */
contract MedicalRecordRegistry {
    struct Record {
        bytes32 recordHash;
        string ipfsCid;
        address uploaderWallet;
        uint256 timestamp;
    }

    address public immutable owner;
    mapping(address => bool) private clinicians;
    mapping(bytes32 => Record) private records;

    event ClinicianAuthorizationChanged(address indexed wallet, bool authorized);
    event RecordRegistered(
        bytes32 indexed recordHash,
        string ipfsCid,
        address indexed uploaderWallet,
        uint256 timestamp
    );

    error Unauthorized();
    error InvalidWallet();
    error InvalidRecordHash();
    error InvalidIpfsCid();
    error RecordAlreadyExists(bytes32 recordHash);
    error RecordNotFound(bytes32 recordHash);

    modifier onlyOwner() {
        if (msg.sender != owner) revert Unauthorized();
        _;
    }

    modifier onlyClinician() {
        if (!clinicians[msg.sender]) revert Unauthorized();
        _;
    }

    constructor() {
        owner = msg.sender;
        clinicians[msg.sender] = true;
        emit ClinicianAuthorizationChanged(msg.sender, true);
    }

    function setClinician(address wallet, bool authorized) external onlyOwner {
        if (wallet == address(0)) revert InvalidWallet();
        clinicians[wallet] = authorized;
        emit ClinicianAuthorizationChanged(wallet, authorized);
    }

    function isClinician(address wallet) external view returns (bool) {
        return clinicians[wallet];
    }

    /** Direct wallet registration for clients that submit their own tx. */
    function registerRecord(bytes32 recordHash, string calldata ipfsCid)
        external
        onlyClinician
    {
        _register(recordHash, ipfsCid, msg.sender);
    }

    /**
     * Relayed registration used by the current backend prototype after the
     * clinician has authenticated by signing a wallet challenge.
     */
    function registerRecordFor(
        bytes32 recordHash,
        string calldata ipfsCid,
        address uploaderWallet
    ) external onlyOwner {
        if (!clinicians[uploaderWallet]) revert Unauthorized();
        _register(recordHash, ipfsCid, uploaderWallet);
    }

    function _register(
        bytes32 recordHash,
        string calldata ipfsCid,
        address uploaderWallet
    ) private {
        if (recordHash == bytes32(0)) revert InvalidRecordHash();
        if (bytes(ipfsCid).length == 0) revert InvalidIpfsCid();
        if (uploaderWallet == address(0)) revert InvalidWallet();
        if (records[recordHash].timestamp != 0) revert RecordAlreadyExists(recordHash);

        uint256 timestamp = block.timestamp;
        records[recordHash] = Record({
            recordHash: recordHash,
            ipfsCid: ipfsCid,
            uploaderWallet: uploaderWallet,
            timestamp: timestamp
        });

        emit RecordRegistered(recordHash, ipfsCid, uploaderWallet, timestamp);
    }

    function verifyRecord(bytes32 recordHash) external view returns (bool) {
        return records[recordHash].timestamp != 0;
    }

    function getRecord(bytes32 recordHash)
        external
        view
        returns (
            bytes32 hash,
            string memory ipfsCid,
            address uploaderWallet,
            uint256 timestamp
        )
    {
        Record storage stored = records[recordHash];
        if (stored.timestamp == 0) revert RecordNotFound(recordHash);
        return (
            stored.recordHash,
            stored.ipfsCid,
            stored.uploaderWallet,
            stored.timestamp
        );
    }
}
