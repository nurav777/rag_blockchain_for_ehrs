import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { api } from "../services/api";

const TOKEN_KEY = "medchain_access_token";
const WALLET_KEY = "medchain_wallet_address";

const AuthContext = createContext(null);

function getStored(key) {
  try {
    return window.localStorage.getItem(key);
  } catch {
    return null;
  }
}

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => getStored(TOKEN_KEY));
  const [walletAddress, setWalletAddress] = useState(() => getStored(WALLET_KEY));
  const [checkingSession, setCheckingSession] = useState(Boolean(getStored(TOKEN_KEY)));

  const persistSession = useCallback((nextToken, nextWallet) => {
    setToken(nextToken);
    setWalletAddress(nextWallet);
    window.localStorage.setItem(TOKEN_KEY, nextToken);
    window.localStorage.setItem(WALLET_KEY, nextWallet);
  }, []);

  const logout = useCallback(() => {
    setToken(null);
    setWalletAddress(null);
    window.localStorage.removeItem(TOKEN_KEY);
    window.localStorage.removeItem(WALLET_KEY);
  }, []);

  const authenticateWithMetaMask = useCallback(async () => {
    if (!window.ethereum) {
      throw new Error("MetaMask was not detected. Install/enable MetaMask and try again.");
    }

    const accounts = await window.ethereum.request({ method: "eth_requestAccounts" });
    const wallet = accounts?.[0];
    if (!wallet) throw new Error("No wallet account was returned by MetaMask.");

    const challenge = await api.challenge(wallet);
    const signature = await window.ethereum.request({
      method: "personal_sign",
      params: [challenge.message, wallet],
    });

    const verified = await api.verifyWallet({
      walletAddress: wallet,
      signature,
      challengeToken: challenge.challenge_token,
    });

    persistSession(verified.access_token, verified.wallet_address || wallet);
    return verified;
  }, [persistSession]);

  useEffect(() => {
    if (!token) {
      setCheckingSession(false);
      return;
    }

    let active = true;
    api.me(token)
      .then((identity) => {
        if (!active) return;
        if (identity?.wallet_address) {
          setWalletAddress(identity.wallet_address);
          window.localStorage.setItem(WALLET_KEY, identity.wallet_address);
        }
      })
      .catch(() => {
        if (active) logout();
      })
      .finally(() => {
        if (active) setCheckingSession(false);
      });

    return () => {
      active = false;
    };
  }, [token, logout]);

  const value = useMemo(() => ({
    token,
    walletAddress,
    isAuthenticated: Boolean(token),
    checkingSession,
    authenticateWithMetaMask,
    logout,
  }), [token, walletAddress, checkingSession, authenticateWithMetaMask, logout]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used inside AuthProvider");
  return context;
}
