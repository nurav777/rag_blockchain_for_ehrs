import { ArrowUp, BrainCircuit, Search as SearchIcon, ShieldCheck, Sparkles } from "lucide-react";
import { useState } from "react";
import CitationCard from "../components/CitationCard";
import LoadingState from "../components/LoadingState";
import { useAuth } from "../hooks/useAuth";
import { api } from "../services/api";

const suggestions = [
  "Which records mention diabetes, and what treatments are described?",
  "Which records describe elevated blood pressure and what medication was prescribed?",
  "Summarize records that mention neuropathy or neurological symptoms.",
];

export default function Search() {
  const { token } = useAuth();
  const [query, setQuery] = useState("");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function submit(event) {
    event?.preventDefault();
    const clean = query.trim();
    if (!clean) return;
    setLoading(true); setError(""); setResult(null);
    try {
      setResult(await api.search(clean, token));
    } catch (err) {
      setError(err.message || "Search failed.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="search-layout">
      <section className="search-primary">
        <div className="query-card">
          <div className="query-card__heading"><div className="feature-icon"><BrainCircuit size={22} /></div><div><span className="eyebrow">Verified RAG</span><h2>Ask across medical records</h2></div></div>
          <form onSubmit={submit} className="query-box">
            <textarea value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Ask a clinical question across the indexed records…" rows={4} />
            <div className="query-box__footer"><span><ShieldCheck size={15} /> Sources are verified before generation</span><button className="send-button" disabled={loading || !query.trim()} type="submit" aria-label="Search"><ArrowUp size={18} /></button></div>
          </form>
          <div className="suggestion-row">{suggestions.map((item) => <button key={item} type="button" onClick={() => setQuery(item)}>{item}</button>)}</div>
        </div>

        {error && <div className="error-banner">{error}</div>}
        {loading && <div className="result-card"><LoadingState label="Retrieving, verifying and generating…" /></div>}
        {result && (
          <article className="result-card">
            <div className="result-card__header"><div><span className="eyebrow">Generated answer</span><h2><Sparkles size={20} /> Grounded response</h2></div><span className="source-count">{result.citations?.length || 0} sources</span></div>
            <div className="answer-text">{result.answer}</div>
          </article>
        )}
      </section>

      <aside className="search-sources">
        <div className="section-heading section-heading--compact"><div><span className="eyebrow">Evidence</span><h2>Retrieved sources</h2></div><SearchIcon size={19} /></div>
        {!result && !loading && <div className="empty-panel"><ShieldCheck size={28} /><h3>Provenance appears here</h3><p>Run a query to inspect the exact record hashes, CIDs, relevance scores and verification state used for generation.</p></div>}
        {result?.citations?.map((citation, index) => <CitationCard key={`${citation.record_hash}-${citation.chunk_index}`} citation={citation} index={index} />)}
      </aside>
    </div>
  );
}
