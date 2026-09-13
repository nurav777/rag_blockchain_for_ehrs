const API_BASE = (import.meta.env.VITE_API_BASE_URL || "").replace(/\/$/, "");
const BESU_RPC_URL = import.meta.env.VITE_BESU_RPC_URL || "/besu-rpc";

function apiUrl(path) {
  return `${API_BASE}${path}`;
}

async function parseResponse(response) {
  const contentType = response.headers.get("content-type") || "";
  const payload = contentType.includes("application/json")
    ? await response.json()
    : await response.text();

  if (!response.ok) {
    const detail = typeof payload === "object" && payload?.detail
      ? payload.detail
      : typeof payload === "string"
        ? payload
        : `Request failed with status ${response.status}`;
    throw new Error(detail);
  }

  return payload;
}

async function request(path, options = {}, token) {
  const headers = new Headers(options.headers || {});
  if (token) headers.set("Authorization", `Bearer ${token}`);

  const response = await fetch(apiUrl(path), {
    ...options,
    headers,
  });

  return parseResponse(response);
}

export const api = {
  challenge(walletAddress) {
    return request("/api/auth/challenge", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ wallet_address: walletAddress }),
    });
  },

  verifyWallet({ walletAddress, signature, challengeToken }) {
    return request("/api/auth/verify", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        wallet_address: walletAddress,
        signature,
        challenge_token: challengeToken,
      }),
    });
  },

  me(token) {
    return request("/api/auth/me", { method: "GET" }, token);
  },

  search(query, token) {
    return request("/api/search/query", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query }),
    }, token);
  },

  uploadRecord(file, token) {
    const form = new FormData();
    form.append("file", file);
    return request("/api/records/upload", {
      method: "POST",
      body: form,
    }, token);
  },

  verifyRecord(recordHash, token) {
    return request(`/api/verify/${encodeURIComponent(recordHash)}`, {
      method: "GET",
    }, token);
  },
};

async function rpc(method, params = []) {
  const response = await fetch(BESU_RPC_URL, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      jsonrpc: "2.0",
      id: Date.now(),
      method,
      params,
    }),
  });

  const payload = await response.json();
  if (!response.ok || payload.error) {
    throw new Error(payload?.error?.message || `Besu RPC request failed (${response.status})`);
  }
  return payload.result;
}

function hexToNumber(hex) {
  return hex == null ? null : Number.parseInt(hex, 16);
}

export const chainApi = {
  rpcUrl: BESU_RPC_URL,

  async getLatestBlocks(limit = 8) {
    const latestHex = await rpc("eth_blockNumber");
    const latest = hexToNumber(latestHex);
    const first = Math.max(0, latest - limit + 1);
    const numbers = [];
    for (let n = latest; n >= first; n -= 1) numbers.push(n);

    const blocks = await Promise.all(
      numbers.map((number) => rpc("eth_getBlockByNumber", [`0x${number.toString(16)}`, true])),
    );

    return blocks.filter(Boolean).map((block) => ({
      number: hexToNumber(block.number),
      hash: block.hash,
      parentHash: block.parentHash,
      timestamp: hexToNumber(block.timestamp),
      gasUsed: hexToNumber(block.gasUsed),
      gasLimit: hexToNumber(block.gasLimit),
      miner: block.miner,
      transactions: block.transactions || [],
    }));
  },

  async getChainId() {
    return hexToNumber(await rpc("eth_chainId"));
  },
};
