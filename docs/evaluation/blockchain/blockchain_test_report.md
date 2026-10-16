# Blockchain Test Report (Local Hardhat)

## Command

```text
cd blockchain && npm test
```

## Result

- **2** tests passed, **0** failed
- Log: `docs/evaluation/blockchain/hardhat_test_console.log`
- Metrics: `docs/evaluation/blockchain/blockchain_metrics.json`

## Scope

Validates `ViolationLogger` Solidity logic on a **local** Hardhat network. Does not measure Sepolia gas, latency, or deployment.

## On-chain content

Contract stores event identifiers and cryptographic hashes of evidence metadata — **not** full video or images (verify against `blockchain/contracts/ViolationLogger.sol`).
