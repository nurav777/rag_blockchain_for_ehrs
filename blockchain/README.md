# Blockchain (Hyperledger Besu)

Local **QBFT consortium** with three validator nodes — one per hospital. Used for medical record **metadata** and integrity verification only. **Medical records are never stored on-chain.**

## Network overview

| Node | Hospital | Role | RPC | P2P (host) |
|------|----------|------|-----|------------|
| `hospital-a` | Hospital A | Validator | **8545** | 30303 |
| `hospital-b` | Hospital B | Validator | — | 30304 |
| `hospital-c` | Hospital C | Validator | — | 30305 |

- **Chain ID:** `1337`
- **Consensus:** QBFT (2s block time)
- **Backend RPC URL:** `http://127.0.0.1:8545` (Hospital A node)

## Project structure

```
blockchain/
├── docker-compose.yml          # Start/stop the 3-node network
├── besu/
│   ├── genesis.json            # QBFT genesis (3 validators)
│   ├── static-nodes.json       # Peer discovery for all nodes
│   ├── nodes/
│   │   ├── hospital-a/         # Validator key + pubkey
│   │   ├── hospital-b/
│   │   └── hospital-c/
│   └── config-input/           # Templates to regenerate keys (optional)
├── contracts/                  # Solidity (to be added)
├── scripts/                    # Deploy/interact scripts (to be added)
└── abi/                        # Compiled ABIs (after deployment)
```

## Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running

## Start the network locally

From the **`blockchain/`** directory:

```powershell
cd f:\rag_blockchain_medical_records\blockchain
docker compose up -d
```

Check status:

```powershell
docker compose ps
docker compose logs -f hospital-a
```

Verify RPC is responding:

```powershell
curl.exe -X POST http://127.0.0.1:8545 ^
  -H "Content-Type: application/json" ^
  -d "{\"jsonrpc\":\"2.0\",\"method\":\"eth_chainId\",\"params\":[],\"id\":1}"
```

Expected result: `"0x539"` (1337 in hex).

## Stop the network

```powershell
docker compose down
```

Remove chain data and start fresh:

```powershell
docker compose down -v
docker compose up -d
```

## Backend configuration

Add to your project root `.env`:

```env
BESU_RPC_URL=http://127.0.0.1:8545
```

## Regenerate network keys (optional)

Only needed if you want new validator keys. From `blockchain/`:

```powershell
docker run --rm --entrypoint /bin/bash `
  -v "${PWD}/besu/config-input:/config" `
  hyperledger/besu:24.12.2 `
  -c "rm -rf /config/generated && besu operator generate-blockchain-config --config-file=/config/qbftConfigFile.json --to=/config/generated --private-key-file-name=key"
```

Then copy `generated/genesis.json` and keys into `besu/` (see `besu/config-input/qbftConfigFile.json`).

> **Note:** Node private keys in `besu/nodes/` are for **local development only**. Never use them on a public network.

## Planned on-chain metadata (future contract)

- Record hash (SHA-256)
- Doctor ID
- Hospital ID
- Timestamp

See [docs/BLOCKCHAIN.md](../docs/BLOCKCHAIN.md).
