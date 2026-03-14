const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function fetchAPI(path: string, options?: RequestInit) {
  const res = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(error.detail || "API request failed");
  }
  return res.json();
}

export async function requestScore(walletAddress: string, agentId?: string) {
  return fetchAPI("/score", {
    method: "POST",
    body: JSON.stringify({
      wallet_address: walletAddress,
      ...(agentId ? { agent_id: agentId } : {}),
    }),
  });
}

export async function getScore(walletAddress: string) {
  return fetchAPI(`/score/${walletAddress}`);
}

export async function getScoreHistory(walletAddress: string) {
  return fetchAPI(`/score/${walletAddress}/history`);
}

export async function getAgent(walletAddress: string) {
  return fetchAPI(`/agents/${walletAddress}`);
}

export async function getAgents(params?: Record<string, string>) {
  const query = params ? "?" + new URLSearchParams(params).toString() : "";
  return fetchAPI(`/agents${query}`);
}

export async function getLeaderboard(tier?: string, limit = 100) {
  const params = new URLSearchParams({ limit: String(limit) });
  if (tier) params.set("tier", tier);
  return fetchAPI(`/leaderboard?${params}`);
}

export async function getStats() {
  return fetchAPI("/stats");
}

export async function getPlatforms() {
  return fetchAPI("/platforms");
}

export async function discoverAgents(
  platform: string,
  page = 1,
  pageSize = 50
) {
  return fetchAPI(
    `/discover/${platform}?page=${page}&page_size=${pageSize}`
  );
}

export async function discoverAllAgents(page = 1, pageSize = 20) {
  return fetchAPI(`/discover?page=${page}&page_size=${pageSize}`);
}

export async function getTransactions(
  walletAddress: string,
  page = 1,
  pageSize = 20
) {
  return fetchAPI(
    `/enrichment/${walletAddress}/transactions?page=${page}&page_size=${pageSize}`
  );
}

export async function getPnL(walletAddress: string) {
  return fetchAPI(`/enrichment/${walletAddress}/pnl`);
}

export async function getPositions(walletAddress: string) {
  return fetchAPI(`/enrichment/${walletAddress}/positions`);
}

export async function searchAgents(query: string, limit = 30) {
  return fetchAPI(`/agents/search?q=${encodeURIComponent(query)}&limit=${limit}`);
}

export async function checkLoanEligibility(walletAddress: string, requestedAmount: number, token = "USDC") {
  return fetchAPI("/lender/eligibility", {
    method: "POST",
    body: JSON.stringify({
      wallet_address: walletAddress,
      requested_amount: requestedAmount,
      token,
    }),
  });
}

export async function applyForLoan(walletAddress: string, amount: number, durationDays: number, token = "USDC") {
  return fetchAPI("/lender/apply", {
    method: "POST",
    body: JSON.stringify({
      wallet_address: walletAddress,
      amount,
      duration_days: durationDays,
      token,
    }),
  });
}
