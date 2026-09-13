import { Navigate, Route, Routes } from "react-router-dom";
import Layout from "./components/Layout";
import ProtectedRoute from "./components/ProtectedRoute";
import Dashboard from "./pages/Dashboard";
import Search from "./pages/Search";
import UploadRecord from "./pages/UploadRecord";
import WalletAuth from "./pages/WalletAuth";
import VerifyRecord from "./pages/VerifyRecord";
import Blockchain from "./pages/Blockchain";

function ProtectedApp() {
  return (
    <ProtectedRoute>
      <Layout />
    </ProtectedRoute>
  );
}

export default function App() {
  return (
    <Routes>
      <Route path="/wallet" element={<WalletAuth />} />
      <Route element={<ProtectedApp />}>
        <Route index element={<Dashboard />} />
        <Route path="/search" element={<Search />} />
        <Route path="/upload" element={<UploadRecord />} />
        <Route path="/verify" element={<VerifyRecord />} />
        <Route path="/blockchain" element={<Blockchain />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
