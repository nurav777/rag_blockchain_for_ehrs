import { Activity, Boxes, FileCheck2, LayoutDashboard, LogOut, Search, UploadCloud, WalletCards } from "lucide-react";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";

const navItems = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard, end: true },
  { to: "/search", label: "Search records", icon: Search },
  { to: "/upload", label: "Upload record", icon: UploadCloud },
  { to: "/verify", label: "Verify record", icon: FileCheck2 },
  { to: "/blockchain", label: "Blockchain", icon: Boxes },
];

const titles = {
  "/": ["Dashboard", "System overview and quick actions"],
  "/search": ["Semantic Search", "Ask questions across blockchain-verified records"],
  "/upload": ["Upload Record", "Pin a PDF, register provenance and index it for RAG"],
  "/verify": ["Verify Record", "Check whether a record hash exists on-chain"],
  "/blockchain": ["Blockchain", "Explore recent blocks from the Besu QBFT network"],
};

function shortWallet(value) {
  return value ? `${value.slice(0, 7)}…${value.slice(-5)}` : "Not connected";
}

export default function Layout() {
  const { walletAddress, logout } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const [title, subtitle] = titles[location.pathname] || titles["/"];

  function signOut() {
    logout();
    navigate("/wallet");
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand__mark"><Activity size={22} /></div>
          <div><strong>MedChain</strong><span>RAG Registry</span></div>
        </div>

        <nav className="sidebar__nav">
          <span className="nav-label">Workspace</span>
          {navItems.map(({ to, label, icon: Icon, end }) => (
            <NavLink key={to} to={to} end={end} className={({ isActive }) => `nav-link ${isActive ? "nav-link--active" : ""}`}>
              <Icon size={18} />
              <span>{label}</span>
            </NavLink>
          ))}
        </nav>

        <div className="sidebar__footer">
          <div className="wallet-mini">
            <WalletCards size={18} />
            <div><span>Clinician wallet</span><strong>{shortWallet(walletAddress)}</strong></div>
          </div>
          <button className="nav-link nav-link--button" onClick={signOut} type="button"><LogOut size={18} /> Sign out</button>
        </div>
      </aside>

      <main className="main-panel">
        <header className="topbar">
          <div><h1>{title}</h1><p>{subtitle}</p></div>
          <div className="network-pill"><span className="network-dot" /> Besu QBFT · Chain 1337</div>
        </header>
        <div className="page-content"><Outlet /></div>
      </main>
    </div>
  );
}
