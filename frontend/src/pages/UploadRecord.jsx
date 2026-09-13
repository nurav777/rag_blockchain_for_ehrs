import { CheckCircle2, FileText, Link2, ShieldCheck, UploadCloud } from "lucide-react";
import { useRef, useState } from "react";
import CopyValue from "../components/CopyValue";
import LoadingState from "../components/LoadingState";
import StatusBadge from "../components/StatusBadge";
import { useAuth } from "../hooks/useAuth";
import { api } from "../services/api";

export default function UploadRecord() {
  const { token, walletAddress } = useAuth();
  const inputRef = useRef(null);
  const [file, setFile] = useState(null);
  const [dragging, setDragging] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState(null);

  function acceptFile(nextFile) {
    setResult(null); setError("");
    if (!nextFile) return;
    if (nextFile.type !== "application/pdf" && !nextFile.name.toLowerCase().endsWith(".pdf")) {
      setError("Only PDF medical records are accepted.");
      return;
    }
    setFile(nextFile);
  }

  async function upload() {
    if (!file) return;
    setLoading(true); setError(""); setResult(null);
    try {
      setResult(await api.uploadRecord(file, token));
    } catch (err) {
      setError(err.message || "Upload failed.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="two-column-page">
      <section className="panel-card">
        <div className="section-heading"><div><span className="eyebrow">New record</span><h2>Upload medical PDF</h2></div><UploadCloud size={22} /></div>
        <div className={`drop-zone ${dragging ? "drop-zone--active" : ""}`} onDragOver={(e) => { e.preventDefault(); setDragging(true); }} onDragLeave={() => setDragging(false)} onDrop={(e) => { e.preventDefault(); setDragging(false); acceptFile(e.dataTransfer.files?.[0]); }} onClick={() => inputRef.current?.click()}>
          <input ref={inputRef} hidden type="file" accept="application/pdf" onChange={(e) => acceptFile(e.target.files?.[0])} />
          <div className="drop-zone__icon"><FileText size={30} /></div>
          {file ? <><h3>{file.name}</h3><p>{(file.size / 1024).toFixed(1)} KB · PDF ready to upload</p></> : <><h3>Drop a PDF record here</h3><p>or click to choose a file from your computer</p></>}
        </div>
        <div className="info-strip"><ShieldCheck size={17} /><span>The authenticated clinician wallet will be stored as provenance; patient identity is not used as application identity.</span></div>
        {error && <div className="error-banner">{error}</div>}
        <button className="button button--primary button--wide" onClick={upload} disabled={!file || loading} type="button">{loading ? "Processing record…" : "Upload & register"}</button>
        {loading && <LoadingState label="Hashing → IPFS → Besu → Chroma…" />}
      </section>

      <aside className="panel-card">
        <div className="section-heading"><div><span className="eyebrow">Pipeline receipt</span><h2>Registration result</h2></div></div>
        {!result ? <div className="empty-panel empty-panel--compact"><Link2 size={28} /><h3>No upload yet</h3><p>The record hash, CID and transaction receipt will appear here.</p></div> : (
          <div className="receipt">
            <div className="receipt__success"><CheckCircle2 size={24} /><div><h3>Record registered</h3><p>The backend completed the storage/provenance pipeline.</p></div></div>
            <div className="receipt-row"><span>Record hash</span><CopyValue value={result.record_hash} compact /></div>
            <div className="receipt-row"><span>IPFS CID</span><CopyValue value={result.ipfs_cid} compact /></div>
            <div className="receipt-row"><span>Transaction</span><CopyValue value={result.tx_hash} compact /></div>
            <div className="receipt-row"><span>Uploader</span><CopyValue value={result.uploader_wallet || walletAddress} compact /></div>
            <div className="receipt-row"><span>Indexing</span><StatusBadge tone={result.indexing_warning ? "warning" : "success"}>{result.indexing_warning || "Indexed successfully"}</StatusBadge></div>
          </div>
        )}
      </aside>
    </div>
  );
}
