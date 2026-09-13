import { FileCheck2, Fingerprint, Link2, Search, ShieldCheck } from "lucide-react";
import { useState } from "react";
import CopyValue from "../components/CopyValue";
import StatusBadge from "../components/StatusBadge";
import { useAuth } from "../hooks/useAuth";
import { api } from "../services/api";

export default function VerifyRecord() {
  const { token } = useAuth();
  const [hash, setHash] = useState("");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function verify(event) {
    event.preventDefault();
    const clean = hash.trim().replace(/^0x/, "");
    if (!clean) return;
    setLoading(true); setError(""); setResult(null);
    try {
      setResult(await api.verifyRecord(clean, token));
    } catch (err) {
      setError(err.message || "Verification failed.");
    } finally {
      setLoading(false);
    }
  }

  const verified = Boolean(result?.verified ?? result?.blockchain_verified ?? result?.exists ?? result?.found);

  return (
    <div className="verify-page">
      <section className="panel-card verify-card">
        <div className="feature-icon feature-icon--large"><Fingerprint size={28} /></div>
        <span className="eyebrow">SHA-256 provenance lookup</span>
        <h2>Verify a medical record</h2>
        <p>Enter the record's SHA-256 hash. The registry lookup checks whether that exact content identity is registered on the consortium blockchain.</p>
        <form onSubmit={verify} className="hash-form"><Search size={18} /><input value={hash} onChange={(e) => setHash(e.target.value)} placeholder="e.g. 9cd76b51d3501d3d…" /><button className="button button--primary" disabled={loading || !hash.trim()} type="submit">{loading ? "Checking…" : "Verify"}</button></form>
        {error && <div className="error-banner">{error}</div>}
      </section>

      {result && (
        <section className={`verification-result ${verified ? "verification-result--good" : "verification-result--bad"}`}>
          <div className="verification-result__hero"><ShieldCheck size={28} /><div><span className="eyebrow">Registry result</span><h2>{verified ? "Record provenance verified" : "Record not found on-chain"}</h2></div><StatusBadge tone={verified ? "verified" : "warning"}>{verified ? "Verified" : "Not verified"}</StatusBadge></div>
          <div className="verification-grid">
            <div><span>Record hash</span><CopyValue value={result.record_hash || hash.trim().replace(/^0x/, "")} compact /></div>
            {result.ipfs_cid && <div><span><Link2 size={14} /> IPFS CID</span><CopyValue value={result.ipfs_cid} compact /></div>}
            {result.uploader_wallet && <div><span>Uploader wallet</span><CopyValue value={result.uploader_wallet} compact /></div>}
            {result.timestamp && <div><span>Registered</span><strong>{new Date(Number(result.timestamp) * 1000).toLocaleString()}</strong></div>}
          </div>
        </section>
      )}
    </div>
  );
}
