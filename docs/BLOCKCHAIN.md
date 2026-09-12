# Blockchain model

`MedicalRecordRegistry` stores an immutable record reference:

- SHA-256 `recordHash`
- IPFS CID
- authorized clinician wallet address
- block timestamp

The contract also contains an allow-list of clinician wallets. The deployer/owner can authorize or revoke clinician wallets. Numeric application identities are not used.

The prototype backend can relay registration after wallet authentication. The contract also exposes direct wallet registration for future clients that submit their own transaction.
