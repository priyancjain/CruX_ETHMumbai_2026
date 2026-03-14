"""
Test script: Call HeyElsa get_transaction_history and print the FULL raw response.
Usage: python test_heyelsa_tx.py [wallet_address]
"""
import asyncio
import json
import sys
from eth_account import Account
from x402 import x402Client
from x402.http.clients import x402HttpxClient
from x402.mechanisms.evm import EthAccountSigner
from x402.mechanisms.evm.exact.register import register_exact_evm_client
from app.config import get_settings


# Default test wallet (Virtuals agent)
DEFAULT_WALLET = "0x17Fd460a86bB57FcBf0062d3AFe199eB54d657E0"


async def test_endpoint(url: str, body: dict, x402_client: x402Client):
    """Call a single x402 endpoint and return raw response."""
    print(f"\n{'='*70}")
    print(f"  CALLING: {url}")
    print(f"  BODY:    {json.dumps(body)}")
    print(f"{'='*70}")

    try:
        async with x402HttpxClient(x402_client, timeout=60) as client:
            resp = await client.post(url, json=body)
            await resp.aread()

            print(f"  STATUS:  {resp.status_code}")
            print(f"  HEADERS: {dict(resp.headers)}")

            if resp.is_success:
                data = resp.json()
                print(f"  RESPONSE TYPE: {type(data).__name__}")

                if isinstance(data, dict):
                    print(f"  TOP-LEVEL KEYS: {list(data.keys())}")
                    for key, value in data.items():
                        val_type = type(value).__name__
                        if isinstance(value, list):
                            print(f"\n  KEY: '{key}' -> list[{len(value)} items]")
                            if value:
                                first = value[0]
                                print(f"    FIRST ITEM TYPE: {type(first).__name__}")
                                if isinstance(first, dict):
                                    print(f"    FIRST ITEM KEYS: {list(first.keys())}")
                                print(f"    FIRST ITEM VALUE: {json.dumps(first, indent=6, default=str)[:500]}")
                                if len(value) > 1:
                                    second = value[1]
                                    print(f"    SECOND ITEM TYPE: {type(second).__name__}")
                                    print(f"    SECOND ITEM VALUE: {json.dumps(second, indent=6, default=str)[:500]}")
                        elif isinstance(value, dict):
                            print(f"\n  KEY: '{key}' -> dict with keys: {list(value.keys())}")
                            print(f"    VALUE: {json.dumps(value, indent=6, default=str)[:500]}")
                        else:
                            print(f"\n  KEY: '{key}' -> {val_type}: {str(value)[:200]}")

                elif isinstance(data, list):
                    print(f"  RESPONSE IS A LIST with {len(data)} items")
                    if data:
                        first = data[0]
                        print(f"    FIRST ITEM TYPE: {type(first).__name__}")
                        print(f"    FIRST ITEM: {json.dumps(first, indent=4, default=str)[:500]}")
                else:
                    print(f"  RAW VALUE: {str(data)[:500]}")

                # Print full raw JSON (truncated)
                raw = json.dumps(data, indent=2, default=str)
                if len(raw) > 3000:
                    print(f"\n  FULL RESPONSE (first 3000 chars):\n{raw[:3000]}...")
                else:
                    print(f"\n  FULL RESPONSE:\n{raw}")

                return data
            else:
                print(f"  ERROR BODY: {resp.text[:500]}")
                return None

    except Exception as e:
        print(f"  EXCEPTION: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return None


async def main():
    wallet = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_WALLET
    print(f"\nTesting HeyElsa x402 endpoints for wallet: {wallet}")

    settings = get_settings()

    if not settings.HEYELSA_WALLET_PRIVATE_KEY:
        print("ERROR: HEYELSA_WALLET_PRIVATE_KEY not set in .env")
        return

    # Build x402 client
    account = Account.from_key(settings.HEYELSA_WALLET_PRIVATE_KEY)
    client = x402Client()
    register_exact_evm_client(client, EthAccountSigner(account))

    base_url = settings.HEYELSA_BASE_URL
    print(f"Base URL: {base_url}")
    print(f"Payer wallet: {account.address}")

    # ── Test 1: analyze_wallet ─────────────────────────────────
    print("\n" + "=" * 70)
    print("  TEST 1: analyze_wallet ($0.02)")
    print("=" * 70)
    analysis = await test_endpoint(
        f"{base_url}/api/analyze_wallet",
        {"wallet_address": wallet},
        client,
    )

    # ── Test 2: get_transaction_history ─────────────────────────
    print("\n" + "=" * 70)
    print("  TEST 2: get_transaction_history ($0.003)")
    print("=" * 70)
    tx_history = await test_endpoint(
        f"{base_url}/api/get_transaction_history",
        {"wallet_address": wallet, "limit": 20},
        client,
    )

    # ── Test 3: get_pnl_report ─────────────────────────────────
    print("\n" + "=" * 70)
    print("  TEST 3: get_pnl_report ($0.015)")
    print("=" * 70)
    pnl = await test_endpoint(
        f"{base_url}/api/get_pnl_report",
        {"wallet_address": wallet, "time_period": "90_days"},
        client,
    )

    # ── Test 4: get_stake_balances ─────────────────────────────
    print("\n" + "=" * 70)
    print("  TEST 4: get_stake_balances ($0.005)")
    print("=" * 70)
    stakes = await test_endpoint(
        f"{base_url}/api/get_stake_balances",
        {"wallet_address": wallet},
        client,
    )

    # ── Summary ────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("  SUMMARY")
    print("=" * 70)
    for name, data in [("analyze_wallet", analysis), ("get_transaction_history", tx_history), ("get_pnl_report", pnl), ("get_stake_balances", stakes)]:
        if data is None:
            print(f"  {name:<30} FAILED (None)")
        elif isinstance(data, dict):
            print(f"  {name:<30} OK (dict, {len(data)} keys: {list(data.keys())[:5]})")
        elif isinstance(data, list):
            print(f"  {name:<30} OK (list, {len(data)} items)")
        else:
            print(f"  {name:<30} OK ({type(data).__name__}: {str(data)[:50]})")


if __name__ == "__main__":
    asyncio.run(main())
