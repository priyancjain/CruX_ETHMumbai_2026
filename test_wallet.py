"""
AgentScore — Wallet Analyzer
Analyzes any wallet on Base Sepolia (testnet) or Base Mainnet.

Usage:
    python test_wallet.py
    python test_wallet.py 0xYOUR_WALLET_ADDRESS

No extra dependencies — uses only Python stdlib.
"""

import sys
import json
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone

# ── Config ────────────────────────────────────────────────────────────────────
WALLET = sys.argv[1] if len(sys.argv) > 1 else "0xCa2A20659F524C663A069A321c4f3e658E58C94b"

# Toggle: set to False to use Base Mainnet
USE_TESTNET = True

if USE_TESTNET:
    NETWORK_LABEL   = "Base Sepolia (Testnet)"
    BLOCKSCOUT_BASE = "https://base-sepolia.blockscout.com/api"
    USDC_CONTRACT   = "0x036CbD53842c5426634e7929541eC2318f3dCF7e"
    CHAIN_ID        = 84532
    EXPLORER_URL    = f"https://sepolia.basescan.org/address/{WALLET}"
else:
    NETWORK_LABEL   = "Base Mainnet"
    BLOCKSCOUT_BASE = "https://base.blockscout.com/api"
    USDC_CONTRACT   = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
    CHAIN_ID        = 8453
    EXPLORER_URL    = f"https://basescan.org/address/{WALLET}"

RESET  = "\033[0m"
BOLD   = "\033[1m"
GREEN  = "\033[92m"
YELLOW = "\033[93m"
RED    = "\033[91m"
CYAN   = "\033[96m"
DIM    = "\033[2m"


# ── Helpers ───────────────────────────────────────────────────────────────────

def fetch(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "AgentScore/1.0"})
    with urllib.request.urlopen(req, timeout=12) as r:
        return json.loads(r.read())


def fmt_eth(wei_hex: str) -> float:
    try:
        return int(wei_hex, 16) / 1e18
    except Exception:
        return 0.0


def ago(ts: int) -> str:
    diff = int(time.time()) - ts
    if diff < 60:        return f"{diff}s ago"
    if diff < 3600:      return f"{diff//60}m ago"
    if diff < 86400:     return f"{diff//3600}h ago"
    if diff < 2592000:   return f"{diff//86400}d ago"
    return f"{diff//2592000}mo ago"


def bar(val: float, max_val: float, width: int = 20) -> str:
    if max_val == 0:
        filled = 0
    else:
        filled = int(min(val / max_val, 1.0) * width)
    return f"{GREEN}{'█' * filled}{DIM}{'░' * (width - filled)}{RESET}"


def section(title: str):
    print(f"\n{BOLD}{CYAN}{'─'*52}{RESET}")
    print(f"{BOLD}{CYAN}  {title}{RESET}")
    print(f"{BOLD}{CYAN}{'─'*52}{RESET}")


# ── Data fetchers ─────────────────────────────────────────────────────────────

def get_eth_balance() -> float:
    try:
        d = fetch(f"{BLOCKSCOUT_BASE}?module=account&action=balance&address={WALLET}")
        return int(d.get("result", "0")) / 1e18
    except:
        return 0.0


def get_usdc_balance() -> float:
    try:
        d = fetch(f"{BLOCKSCOUT_BASE}?module=account&action=tokenbalance"
                  f"&contractaddress={USDC_CONTRACT}&address={WALLET}")
        return int(d.get("result", "0")) / 1e6
    except:
        return 0.0


def get_transactions(limit: int = 100) -> list:
    try:
        d = fetch(f"{BLOCKSCOUT_BASE}?module=account&action=txlist"
                  f"&address={WALLET}&page=1&offset={limit}&sort=desc")
        result = d.get("result", [])
        return result if isinstance(result, list) else []
    except:
        return []


def get_token_transfers() -> list:
    try:
        d = fetch(f"{BLOCKSCOUT_BASE}?module=account&action=tokentx"
                  f"&address={WALLET}&page=1&offset=50&sort=desc")
        result = d.get("result", [])
        return result if isinstance(result, list) else []
    except:
        return []


def get_internal_txs() -> list:
    try:
        d = fetch(f"{BLOCKSCOUT_BASE}?module=account&action=txlistinternal"
                  f"&address={WALLET}&page=1&offset=20&sort=desc")
        result = d.get("result", [])
        return result if isinstance(result, list) else []
    except:
        return []


# ── Analysis ──────────────────────────────────────────────────────────────────

def analyze_transactions(txs: list) -> dict:
    if not txs:
        return {
            "total": 0, "sent": 0, "received": 0,
            "last_90d": 0, "unique_contracts": 0,
            "wallet_age_days": 0, "first_tx": None, "last_tx": None,
            "avg_value_eth": 0, "max_value_eth": 0,
        }

    now = int(time.time())
    cutoff_90d = now - 90 * 86400

    sent, received, last_90d = 0, 0, 0
    contracts = set()
    values = []
    timestamps = []

    for tx in txs:
        ts = int(tx.get("timeStamp", 0))
        timestamps.append(ts)
        value_eth = int(tx.get("value", "0")) / 1e18

        if tx.get("from", "").lower() == WALLET.lower():
            sent += 1
        else:
            received += 1
            values.append(value_eth)

        if ts >= cutoff_90d:
            last_90d += 1

        to_addr = tx.get("to", "")
        if to_addr and to_addr != WALLET.lower() and tx.get("input", "0x") != "0x":
            contracts.add(to_addr.lower())

    timestamps.sort()
    first_ts = timestamps[0] if timestamps else now
    last_ts  = timestamps[-1] if timestamps else now
    age_days = (now - first_ts) // 86400

    return {
        "total":              len(txs),
        "sent":               sent,
        "received":           received,
        "last_90d":           last_90d,
        "unique_contracts":   len(contracts),
        "wallet_age_days":    age_days,
        "first_tx":           datetime.fromtimestamp(first_ts, tz=timezone.utc).strftime("%Y-%m-%d") if timestamps else None,
        "last_tx":            ago(last_ts) if timestamps else None,
        "avg_value_eth":      sum(values) / len(values) if values else 0,
        "max_value_eth":      max(values) if values else 0,
    }


def analyze_tokens(transfers: list) -> dict:
    tokens = {}
    protocols = set()
    for t in transfers:
        sym = t.get("tokenSymbol", "?")
        tokens[sym] = tokens.get(sym, 0) + 1
        contract = t.get("contractAddress", "").lower()
        if contract:
            protocols.add(contract)

    return {
        "unique_tokens":    len(tokens),
        "token_list":       list(tokens.keys())[:10],
        "transfer_count":   len(transfers),
        "protocol_count":   len(protocols),
    }


def score_wallet(eth: float, usdc: float, tx_data: dict, token_data: dict) -> dict:
    """Simple local scoring — mirrors AgentScore pipeline logic."""
    score = 0
    factors = []
    flags = []

    # Wallet age (max 200 pts)
    age = tx_data["wallet_age_days"]
    if age >= 365:
        score += 200; factors.append("Wallet age > 1 year")
    elif age >= 180:
        score += 150; factors.append("Wallet age > 6 months")
    elif age >= 90:
        score += 100; factors.append("Wallet age > 3 months")
    elif age >= 30:
        score += 50;  factors.append("Wallet age > 1 month")
    elif age > 0:
        score += 20;  flags.append("Very new wallet (< 30 days)")
    else:
        flags.append("New wallet — no transaction history")

    # Transaction count (max 250 pts)
    total = tx_data["total"]
    if total >= 500:
        score += 250; factors.append("High transaction volume (500+)")
    elif total >= 100:
        score += 180; factors.append("Good transaction volume (100+)")
    elif total >= 50:
        score += 120; factors.append("Moderate activity (50+)")
    elif total >= 10:
        score += 60;  factors.append("Some activity (10+)")
    elif total > 0:
        score += 20;  flags.append("Low activity (< 10 txs)")
    else:
        flags.append("No transactions found")

    # 90-day activity (max 150 pts)
    recent = tx_data["last_90d"]
    if recent >= 50:
        score += 150; factors.append("Very active in last 90 days")
    elif recent >= 20:
        score += 100; factors.append("Active in last 90 days")
    elif recent >= 5:
        score += 50;  factors.append("Moderate recent activity")
    else:
        flags.append("Low recent activity (< 5 txs in 90d)")

    # ETH balance (max 100 pts)
    if eth >= 1.0:
        score += 100; factors.append("Strong ETH holdings")
    elif eth >= 0.1:
        score += 70;  factors.append("Decent ETH balance")
    elif eth >= 0.01:
        score += 30
    elif eth > 0:
        score += 10;  flags.append("Very low ETH balance")
    else:
        flags.append("Zero ETH balance")

    # USDC balance (max 100 pts)
    if usdc >= 10000:
        score += 100; factors.append("Large USDC holdings")
    elif usdc >= 1000:
        score += 70;  factors.append("Good USDC holdings")
    elif usdc >= 100:
        score += 40
    elif usdc >= 1:
        score += 15
    else:
        flags.append("No USDC balance")

    # DeFi diversity (max 100 pts)
    protocols = token_data["protocol_count"]
    if protocols >= 10:
        score += 100; factors.append("High DeFi diversity (10+ protocols)")
    elif protocols >= 5:
        score += 70;  factors.append("Good DeFi diversity")
    elif protocols >= 2:
        score += 40
    elif protocols == 1:
        score += 15

    # Token diversity (max 50 pts)
    tokens = token_data["unique_tokens"]
    if tokens >= 10:
        score += 50; factors.append("Diverse token portfolio")
    elif tokens >= 5:
        score += 30
    elif tokens >= 2:
        score += 15

    # Contract interaction (max 50 pts)
    contracts = tx_data["unique_contracts"]
    if contracts >= 20:
        score += 50; factors.append("Heavy smart contract usage")
    elif contracts >= 10:
        score += 35
    elif contracts >= 5:
        score += 20
    elif contracts >= 1:
        score += 10

    score = min(score, 1000)

    # Tier
    if score >= 900: tier = "S"
    elif score >= 750: tier = "A"
    elif score >= 600: tier = "B"
    elif score >= 450: tier = "C"
    else: tier = "D"

    # Collateral & max loan
    tier_map = {
        "S": (30, 500_000),
        "A": (75, 100_000),
        "B": (120, 25_000),
        "C": (150, 5_000),
        "D": (200, 1_000),
    }
    collateral, max_loan = tier_map[tier]

    return {
        "score": score,
        "tier": tier,
        "collateral_pct": collateral,
        "max_loan_usdc": max_loan,
        "key_factors": factors,
        "risk_flags": flags,
    }


# ── Main ──────────────────────────────────────────────────────────────────────

print(f"\n{BOLD}{'━'*52}{RESET}")
print(f"{BOLD}  AgentScore — Wallet Analyzer{RESET}")
print(f"{BOLD}{'━'*52}{RESET}")
print(f"  Wallet  : {BOLD}{WALLET}{RESET}")
print(f"  Network : {NETWORK_LABEL}")
print(f"  Explorer: {DIM}{EXPLORER_URL}{RESET}")

# ── Fetch all data ─────────────────────────────────────────────────────────────
section("1 / 4  Fetching Balances")
print("  Checking ETH balance ...", end="\r")
eth = get_eth_balance()
print(f"  ETH Balance  : {BOLD}{eth:.6f} ETH{RESET}  {GREEN+'✓' if eth > 0 else RED+'✗ empty'}{RESET}")

print("  Checking USDC balance ...", end="\r")
usdc = get_usdc_balance()
print(f"  USDC Balance : {BOLD}{usdc:.4f} USDC{RESET}  {GREEN+'✓' if usdc > 0 else RED+'✗ empty'}{RESET}")

section("2 / 4  Fetching Transactions")
print("  Loading transactions ...", end="\r")
txs = get_transactions(100)
tx_data = analyze_transactions(txs)
print(f"  Total TXs    : {BOLD}{tx_data['total']}{RESET}")
print(f"  Sent         : {tx_data['sent']}")
print(f"  Received     : {tx_data['received']}")
print(f"  Last 90 days : {tx_data['last_90d']} txs")
print(f"  Wallet Age   : {BOLD}{tx_data['wallet_age_days']} days{RESET}", end="")
if tx_data["first_tx"]:
    print(f"  (since {tx_data['first_tx']})")
else:
    print()
if tx_data["last_tx"]:
    print(f"  Last TX      : {tx_data['last_tx']}")
print(f"  Contracts Used: {tx_data['unique_contracts']} unique")

section("3 / 4  Fetching Token Activity")
print("  Loading token transfers ...", end="\r")
transfers = get_token_transfers()
token_data = analyze_tokens(transfers)
print(f"  Token Transfers : {token_data['transfer_count']}")
print(f"  Unique Tokens   : {token_data['unique_tokens']}")
if token_data["token_list"]:
    print(f"  Tokens Seen     : {', '.join(token_data['token_list'])}")
print(f"  DeFi Protocols  : {token_data['protocol_count']}")

section("4 / 4  AgentScore (Local Estimate)")
result = score_wallet(eth, usdc, tx_data, token_data)

TIER_COLOR = {"S": YELLOW, "A": GREEN, "B": CYAN, "C": "\033[33m", "D": RED}
tc = TIER_COLOR.get(result["tier"], "")

score = result["score"]
print(f"\n  Score    : {BOLD}{tc}{score} / 1000{RESET}  {bar(score, 1000)}")
print(f"  Tier     : {BOLD}{tc}{result['tier']}{RESET}")
print(f"  Collateral Required : {result['collateral_pct']}%")
print(f"  Max DeFi Loan       : ${result['max_loan_usdc']:,} USDC")

if result["key_factors"]:
    print(f"\n  {BOLD}Positive Signals:{RESET}")
    for f in result["key_factors"]:
        print(f"    {GREEN}✓{RESET} {f}")

if result["risk_flags"]:
    print(f"\n  {BOLD}Risk Flags:{RESET}")
    for f in result["risk_flags"]:
        print(f"    {YELLOW}⚠{RESET}  {f}")

# ── What this wallet needs ─────────────────────────────────────────────────────
section("ACTION ITEMS  (to improve score)")
actions = []
if eth == 0:
    actions.append(("ETH needed for gas", "https://www.alchemy.com/faucets/base-sepolia"))
if usdc < 5:
    actions.append(("Get more USDC (testnet)", "https://faucet.circle.com"))
if tx_data["total"] < 10:
    actions.append(("More transaction history needed", "Make some on-chain interactions"))
if tx_data["wallet_age_days"] < 30:
    actions.append(("Wallet is very new", "Age builds score over time"))
if token_data["protocol_count"] < 3:
    actions.append(("Interact with more DeFi protocols", "Try Uniswap, Aave on Base Sepolia"))

if actions:
    for desc, link in actions:
        print(f"  → {desc}")
        print(f"    {DIM}{link}{RESET}")
else:
    print(f"  {GREEN}✓ Wallet looks healthy — run full scoring via the API{RESET}")

print(f"\n{BOLD}{'━'*52}{RESET}")
print(f"  {DIM}Note: This is a LOCAL estimate only.{RESET}")
print(f"  {DIM}For the full GPT-o3 score, run:{RESET}")
print(f"  {BOLD}python test_agentscore.py {WALLET}{RESET}")
print(f"{BOLD}{'━'*52}{RESET}\n")
