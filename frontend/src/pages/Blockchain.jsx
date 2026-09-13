import { Boxes, CircleAlert, RefreshCw, Route, ShieldCheck } from "lucide-react";
import { useEffect, useState } from "react";
import CopyValue from "../components/CopyValue";
import LoadingState from "../components/LoadingState";
import StatusBadge from "../components/StatusBadge";
import { chainApi } from "../services/api";

function BlockCard({ block, selected, onSelect }) {
  const date = block.timestamp ? new Date(block.timestamp * 1000) : null;
  return (
    <button type="button" className={`block-node ${selected ? "block-node--selected" : ""}`} onClick={() => onSelect(block)}>
      <div className="block-node__top"><span>BLOCK</span><strong>#{block.number}</strong></div>
      <div className="block-node__hash">{block.hash?.slice(0, 12)}…{block.hash?.slice(-8)}</div>
      <div className="block-node__meta"><span>{block.transactions.length} tx</span><span>{date?.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" })}</span></div>
    </button>
  );
}

export default function Blockchain() {
  const [blocks, setBlocks] = useState([]);
  const [chainId, setChainId] = useState(null);
  const [selected, setSelected] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function load() {
    setLoading(true); setError("");
    try {
      const [id, recent] = await Promise.all([chainApi.getChainId(), chainApi.getLatestBlocks(8)]);
      setChainId(id); setBlocks(recent); setSelected((current) => current || recent[0] || null);
    } catch (err) {
      setError(`${err.message}. If Besu is healthy, this is usually browser CORS; see the README for the RPC setting.`);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, []);

  return (
    <div className="stack-xl">
      <section className="chain-summary">
        <div><span className="eyebrow">Live consortium ledger</span><h2>Besu QBFT block explorer</h2><p>Recent blocks are read from the configured JSON-RPC endpoint and drawn as a linked chain. Select any block to inspect its metadata and transactions.</p></div>
        <div className="chain-summary__meta"><StatusBadge tone="verified"><ShieldCheck size={14} /> QBFT network</StatusBadge><span>Chain ID <strong>{chainId ?? import.meta.env.VITE_CHAIN_ID ?? 1337}</strong></span><button className="button button--secondary button--small" onClick={load} disabled={loading}><RefreshCw size={15} /> Refresh</button></div>
      </section>

      {loading && <div className="panel-card"><LoadingState label="Reading recent blocks from Besu…" /></div>}
      {error && <div className="error-banner error-banner--large"><CircleAlert size={18} /> {error}<small>RPC: {chainApi.rpcUrl}</small></div>}

      {!loading && !error && (
        <>
          <section className="chain-canvas">
            <div className="chain-canvas__label"><Route size={17} /> Newest → oldest</div>
            <div className="block-chain">
              {blocks.map((block, index) => (
                <div className="block-chain__item" key={block.hash}>
                  <BlockCard block={block} selected={selected?.hash === block.hash} onSelect={setSelected} />
                  {index < blocks.length - 1 && <div className="chain-link"><span /><span /><span /></div>}
                </div>
              ))}
            </div>
          </section>

          {selected && (
            <section className="block-inspector panel-card">
              <div className="section-heading"><div><span className="eyebrow">Block metadata</span><h2>Block #{selected.number}</h2></div><Boxes size={22} /></div>
              <div className="verification-grid">
                <div><span>Block hash</span><CopyValue value={selected.hash} compact /></div>
                <div><span>Parent hash</span><CopyValue value={selected.parentHash} compact /></div>
                <div><span>Timestamp</span><strong>{new Date(selected.timestamp * 1000).toLocaleString()}</strong></div>
                <div><span>Transactions</span><strong>{selected.transactions.length}</strong></div>
                <div><span>Gas used</span><strong>{selected.gasUsed?.toLocaleString()}</strong></div>
                <div><span>Gas limit</span><strong>{selected.gasLimit?.toLocaleString()}</strong></div>
              </div>

              <div className="tx-list">
                <span className="eyebrow">Transactions</span>
                {selected.transactions.length === 0 ? <div className="empty-inline">No transactions in this block.</div> : selected.transactions.map((tx, index) => (
                  <div className="tx-row" key={tx.hash || index}>
                    <span className="tx-index">TX {String(index + 1).padStart(2, "0")}</span>
                    <div><span>Hash</span><CopyValue value={tx.hash} compact /></div>
                    <div><span>From</span><CopyValue value={tx.from} compact /></div>
                    <div><span>To</span><CopyValue value={tx.to || "Contract creation"} compact={Boolean(tx.to)} /></div>
                  </div>
                ))}
              </div>
            </section>
          )}
        </>
      )}
    </div>
  );
}
