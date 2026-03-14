"""
Deploy AgentScoreAnchor to Base Sepolia from Python.

Usage:
    python contracts/deploy.py

Requires:
    - SCORE_ANCHOR_PRIVATE_KEY in backend/.env (or pass as arg)
    - Base Sepolia ETH in the deployer wallet for gas
    - py-solc-x and web3 installed
"""
import sys
import os
import json

# Add backend to path so we can import config
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

import solcx
from web3 import Web3


def deploy():
    # ── Config ───────────────────────────────────────────────────────────
    RPC_URL = "https://sepolia.base.org"
    CHAIN_ID = 84532

    # Try to load private key from backend/.env
    private_key = os.environ.get("SCORE_ANCHOR_PRIVATE_KEY", "")
    if not private_key:
        env_path = os.path.join(os.path.dirname(__file__), "..", "backend", ".env")
        if os.path.exists(env_path):
            with open(env_path) as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("SCORE_ANCHOR_PRIVATE_KEY="):
                        private_key = line.split("=", 1)[1].strip().strip('"').strip("'")
                        break

    if not private_key:
        print("ERROR: Set SCORE_ANCHOR_PRIVATE_KEY in backend/.env or as env var")
        sys.exit(1)

    # ── Compile ──────────────────────────────────────────────────────────
    print("Installing solc 0.8.20...")
    solcx.install_solc("0.8.20")

    contract_path = os.path.join(os.path.dirname(__file__), "AgentScoreAnchor.sol")
    with open(contract_path) as f:
        source = f.read()

    print("Compiling AgentScoreAnchor.sol...")
    compiled = solcx.compile_source(
        source,
        output_values=["abi", "bin"],
        solc_version="0.8.20",
    )

    contract_id = "<stdin>:AgentScoreAnchor"
    abi = compiled[contract_id]["abi"]
    bytecode = compiled[contract_id]["bin"]

    print(f"Compiled OK — bytecode size: {len(bytecode) // 2} bytes")

    # ── Deploy ───────────────────────────────────────────────────────────
    w3 = Web3(Web3.HTTPProvider(RPC_URL))
    if not w3.is_connected():
        print(f"ERROR: Cannot connect to {RPC_URL}")
        sys.exit(1)

    account = w3.eth.account.from_key(private_key)
    balance = w3.eth.get_balance(account.address)
    balance_eth = w3.from_wei(balance, "ether")
    print(f"Deployer: {account.address}")
    print(f"Balance:  {balance_eth} ETH (Base Sepolia)")

    if balance == 0:
        print("\nERROR: No Base Sepolia ETH. Get some from:")
        print("  https://www.alchemy.com/faucets/base-sepolia")
        sys.exit(1)

    contract = w3.eth.contract(abi=abi, bytecode=bytecode)

    print("\nDeploying AgentScoreAnchor...")
    tx = contract.constructor().build_transaction({
        "from": account.address,
        "nonce": w3.eth.get_transaction_count(account.address),
        "gas": 500000,
        "maxFeePerGas": w3.to_wei(0.1, "gwei"),
        "maxPriorityFeePerGas": w3.to_wei(0.05, "gwei"),
        "chainId": CHAIN_ID,
    })

    signed = w3.eth.account.sign_transaction(tx, private_key)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    print(f"TX sent: {tx_hash.hex()}")

    print("Waiting for confirmation...")
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)

    if receipt["status"] != 1:
        print("ERROR: Deployment transaction reverted!")
        sys.exit(1)

    contract_address = receipt["contractAddress"]
    print(f"\n{'='*60}")
    print(f"  AgentScoreAnchor deployed!")
    print(f"  Contract: {contract_address}")
    print(f"  TX Hash:  {tx_hash.hex()}")
    print(f"  Block:    {receipt['blockNumber']}")
    print(f"  Gas Used: {receipt['gasUsed']}")
    print(f"{'='*60}")

    print(f"\nAdd to backend/.env:")
    print(f"  SCORE_ANCHOR_ADDRESS={contract_address}")

    # Save ABI for frontend use
    abi_path = os.path.join(os.path.dirname(__file__), "AgentScoreAnchor.json")
    with open(abi_path, "w") as f:
        json.dump({"address": contract_address, "abi": abi}, f, indent=2)
    print(f"\nABI saved to: {abi_path}")

    # Try to auto-update backend/.env
    env_path = os.path.join(os.path.dirname(__file__), "..", "backend", ".env")
    if os.path.exists(env_path):
        with open(env_path) as f:
            env_content = f.read()
        if "SCORE_ANCHOR_ADDRESS=" in env_content:
            env_content = "\n".join(
                f"SCORE_ANCHOR_ADDRESS={contract_address}" if line.startswith("SCORE_ANCHOR_ADDRESS=") else line
                for line in env_content.splitlines()
            )
        else:
            env_content += f"\nSCORE_ANCHOR_ADDRESS={contract_address}\n"
        with open(env_path, "w") as f:
            f.write(env_content)
        print(f"Updated backend/.env with SCORE_ANCHOR_ADDRESS")


if __name__ == "__main__":
    deploy()
