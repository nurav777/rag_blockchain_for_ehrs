import { Activity, ArrowRight, Boxes, KeyRound, ShieldCheck, WalletCards } from "lucide-react";
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";

export default function WalletAuth() {
  const { authenticateWithMetaMask, isAuthenticated } = useAuth();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const navigate = useNavigate();

  useEffect(() => {
    if (isAuthenticated) navigate("/", { replace: true });
  }, [isAuthenticated, navigate]);

  async function connect() {
    setError("");
    setLoading(true);
    try {
      await authenticateWithMetaMask();
      navigate("/", { replace: true });
    } catch (err) {
      setError(err.message || "Wallet authentication failed.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="auth-page">
      <section className="auth-hero">
        <div className="brand brand--large">
          <div className="brand__mark"><Activity size={24} /></div>
          <div><strong>MedChain</strong><span>RAG Registry</span></div>
        </div>
        <div className="auth-hero__content">
          <span className="hero-kicker">CONSORTIUM MEDICAL RECORD INTELLIGENCE</span>
          <h1>Ask records.<br /><em>Verify provenance.</em></h1>
          <p>A wallet-authenticated RAG interface backed by IPFS content addressing and a Hyperledger Besu QBFT registry.</p>
        </div>
        <div className="auth-proof-grid">
          <div><ShieldCheck size={20} /><span>On-chain provenance</span></div>
          <div><Boxes size={20} /><span>IPFS-backed records</span></div>
          <div><KeyRound size={20} /><span>Wallet identity</span></div>
        </div>
      </section>

      <section className="auth-panel">
        <div className="auth-card">
          <div className="auth-card__icon"><WalletCards size={28} /></div>
          <span className="eyebrow">Clinician access</span>
          <h2>Authenticate your wallet</h2>
          <p>Connect an authorized clinician wallet. You will sign a short-lived challenge; your private key never leaves MetaMask.</p>

          <div className="auth-steps">
            <div><span>01</span><p><strong>Connect</strong> an authorized wallet</p></div>
            <div><span>02</span><p><strong>Sign</strong> the backend challenge</p></div>
            <div><span>03</span><p><strong>Access</strong> verified RAG tools</p></div>
          </div>

          {error && <div className="error-banner">{error}</div>}

          <button className="button button--primary button--wide" onClick={connect} disabled={loading} type="button">
            {loading ? "Waiting for signature…" : "Connect with MetaMask"}
            {!loading && <ArrowRight size={18} />}
          </button>
          <small className="muted centered">Only wallets authorized on the MedicalRecordRegistry contract can continue.</small>
        </div>
      </section>
    </div>
  );
}
