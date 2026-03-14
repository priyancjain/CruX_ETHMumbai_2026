"""
Test ENSIP-25 reverse resolution with known ENS wallets.
Usage: python test_ensip25.py [wallet_address]
"""
import asyncio
import sys
import logging

logging.basicConfig(level=logging.DEBUG, format="%(name)-40s │ %(message)s")

# Test wallets with known ENS names
KNOWN_ENS_WALLETS = {
    "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045": "vitalik.eth",
}

# Default test wallet (no ENS name — Virtuals agent)
DEFAULT_WALLET = "0x12C1255c35A7F6afC3fedd16A6a44Edc213B9F7B"


async def test_wallet(wallet: str, expected_name: str | None = None):
    from app.services.ensip25 import check_ensip25, _namehash, _reverse_resolve

    print(f"\n{'='*60}")
    print(f"  Testing ENSIP-25 for: {wallet}")
    if expected_name:
        print(f"  Expected ENS name:   {expected_name}")
    print(f"{'='*60}")

    # Step 0: Test _namehash with known values
    print(f"\n  [Step 0] Testing _namehash...")
    eth_hash = _namehash("eth")
    expected_eth = "0x93cdeb708b7545dc668eb9280176169d1c33cfd8ed6f04690a0bcc88a93fc4ae"
    print(f"    namehash('eth') = {eth_hash}")
    print(f"    Expected:         {expected_eth}")
    print(f"    Match: {eth_hash == expected_eth}")

    if expected_name:
        name_hash = _namehash(expected_name)
        print(f"    namehash('{expected_name}') = {name_hash}")

    # Step 1: Test reverse resolution
    print(f"\n  [Step 1] Testing reverse resolution...")
    from app.config import get_settings
    settings = get_settings()
    rpc_url = settings.ALCHEMY_ETH_RPC
    print(f"    RPC URL: {rpc_url[:50]}...")

    ens_name = await _reverse_resolve(wallet, rpc_url)
    print(f"    Resolved ENS name: {ens_name or '(none)'}")
    if expected_name:
        if ens_name == expected_name:
            print(f"    PASS: Matches expected '{expected_name}'")
        else:
            print(f"    FAIL: Expected '{expected_name}', got '{ens_name}'")

    # Step 2: Test full check_ensip25
    print(f"\n  [Step 2] Testing full check_ensip25...")
    result = await check_ensip25(wallet, agent_id="0")
    print(f"    Result: {result}")
    print(f"    ENS name:          {result.get('ens_name') or '(none)'}")
    print(f"    ENSIP-25 verified: {result.get('ensip25_verified', False)}")
    if result.get("text_key"):
        print(f"    Text key:          {result.get('text_key')}")
        print(f"    Text value:        {result.get('text_value') or '(empty)'}")

    return result


async def main():
    wallet = sys.argv[1] if len(sys.argv) > 1 else None

    if wallet:
        expected = KNOWN_ENS_WALLETS.get(wallet)
        await test_wallet(wallet, expected)
    else:
        # Test all known wallets + default
        for addr, expected_name in KNOWN_ENS_WALLETS.items():
            await test_wallet(addr, expected_name)

        print(f"\n{'='*60}")
        print(f"  Now testing a wallet WITHOUT ENS name:")
        print(f"{'='*60}")
        await test_wallet(DEFAULT_WALLET, None)


if __name__ == "__main__":
    asyncio.run(main())
