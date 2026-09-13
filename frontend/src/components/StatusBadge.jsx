import { CheckCircle2, CircleAlert, Clock3, ShieldCheck } from "lucide-react";

const icons = {
  verified: ShieldCheck,
  success: CheckCircle2,
  warning: CircleAlert,
  neutral: Clock3,
};

export default function StatusBadge({ tone = "neutral", children }) {
  const Icon = icons[tone] || Clock3;
  return (
    <span className={`status-badge status-badge--${tone}`}>
      <Icon size={14} />
      {children}
    </span>
  );
}
