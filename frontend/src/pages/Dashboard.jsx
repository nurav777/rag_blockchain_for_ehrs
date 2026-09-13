import { ArrowRight, Boxes, FileCheck2, Search, ShieldCheck, UploadCloud, WalletCards } from "lucide-react";
import { Link } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";
import CopyValue from "../components/CopyValue";
import StatusBadge from "../components/StatusBadge";

const actions = [
  { to: "/search", icon: Search, title: "Ask medical records", text: "Run semantic retrieval and generate a grounded answer." },
  { to: "/upload", icon: UploadCloud, title: "Upload a PDF", text: "Pin, register and index a new medical record." },
  { to: "/verify", icon: FileCheck2, title: "Verify provenance", text: "Resolve a SHA-256 record hash against the registry." },
  { to: "/blockchain", icon: Boxes, title: "Explore the chain", text: "Inspect recent Besu blocks and transaction metadata." },
];

export default function Dashboard() {
  const { walletAddress } = useAuth();

  return (
    <div className="stack-xl">
      <section className="hero-card">
        <div>
          <StatusBadge tone="verified">Authenticated clinician</StatusBadge>
          <h2>Trusted retrieval, from query to provenance.</h2>
          <p>Search is grounded in IPFS-hosted documents whose content hashes are checked against your Besu registry before context reaches the local language model.</p>
          <div className="hero-actions"><Link className="button button--primary" to="/search">Start searching <ArrowRight size={17} /></Link><Link className="button button--secondary" to="/upload">Upload record</Link></div>
        </div>
        <div className="hero-orbit" aria-hidden="true"><div className="orbit orbit--1" /><div className="orbit orbit--2" /><div className="orbit-core"><ShieldCheck size={30} /></div></div>
      </section>

      <section className="stat-grid">
        <article className="stat-card"><div className="stat-card__icon"><WalletCards size={20} /></div><span>Active identity</span><CopyValue value={walletAddress} compact /></article>
        <article className="stat-card"><div className="stat-card__icon"><Boxes size={20} /></div><span>Consensus network</span><strong>Besu QBFT · 3 validators</strong></article>
        <article className="stat-card"><div className="stat-card__icon"><ShieldCheck size={20} /></div><span>Retrieval policy</span><strong>Blockchain verification required</strong></article>
      </section>

      <section>
        <div className="section-heading"><div><span className="eyebrow">Workspace</span><h2>What do you want to do?</h2></div></div>
        <div className="action-grid">
          {actions.map(({ to, icon: Icon, title, text }) => (
            <Link to={to} className="action-card" key={to}>
              <div className="action-card__icon"><Icon size={20} /></div>
              <h3>{title}</h3><p>{text}</p><span className="action-card__link">Open tool <ArrowRight size={15} /></span>
            </Link>
          ))}
        </div>
      </section>

      <section className="pipeline-card">
        <div className="section-heading"><div><span className="eyebrow">Retrieval path</span><h2>How a query becomes a verified answer</h2></div></div>
        <div className="pipeline">
          {["Semantic query", "Chroma match", "Record hash", "Besu registry", "IPFS document", "Local LLM"].map((label, index) => (
            <div className="pipeline__step" key={label}><span>{String(index + 1).padStart(2, "0")}</span><strong>{label}</strong>{index < 5 && <i>→</i>}</div>
          ))}
        </div>
      </section>
    </div>
  );
}
