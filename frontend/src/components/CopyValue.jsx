import { Check, Copy } from "lucide-react";
import { useState } from "react";

export default function CopyValue({ value, compact = false }) {
  const [copied, setCopied] = useState(false);
  const display = compact && value && value.length > 20
    ? `${value.slice(0, 10)}…${value.slice(-8)}`
    : value;

  async function copy() {
    await navigator.clipboard.writeText(value || "");
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1400);
  }

  return (
    <span className="copy-value">
      <code title={value}>{display || "—"}</code>
      {value && (
        <button className="icon-button" onClick={copy} type="button" aria-label="Copy value">
          {copied ? <Check size={15} /> : <Copy size={15} />}
        </button>
      )}
    </span>
  );
}
