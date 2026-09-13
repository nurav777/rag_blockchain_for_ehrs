import { ChevronDown, FileText, Link2, ShieldCheck } from "lucide-react";
import CopyValue from "./CopyValue";
import StatusBadge from "./StatusBadge";

export default function CitationCard({ citation, index }) {
  const score = Number(citation.score || 0);
  return (
    <article className="citation-card">
      <div className="citation-card__header">
        <div className="citation-icon"><FileText size={19} /></div>
        <div>
          <span className="eyebrow">Source {String(index + 1).padStart(2, "0")}</span>
          <h3>Verified medical record</h3>
        </div>
        <StatusBadge tone={citation.blockchain_verified ? "verified" : "warning"}>
          {citation.blockchain_verified ? "Blockchain verified" : "Unverified"}
        </StatusBadge>
      </div>

      <div className="citation-metrics">
        <div><span>Relevance</span><strong>{score.toFixed(3)}</strong></div>
        <div><span>Chunk</span><strong>#{citation.chunk_index}</strong></div>
        <div><span>Source</span><strong>{citation.source || "IPFS"}</strong></div>
      </div>

      <details className="details-panel">
        <summary><ChevronDown size={16} /> View provenance & excerpt</summary>
        <div className="details-panel__body">
          <div className="detail-row"><span><ShieldCheck size={15} /> Record hash</span><CopyValue value={citation.record_hash} compact /></div>
          <div className="detail-row"><span><Link2 size={15} /> IPFS CID</span><CopyValue value={citation.ipfs_cid} compact /></div>
          <p className="citation-excerpt">{citation.excerpt}</p>
        </div>
      </details>
    </article>
  );
}
