import { Navigate } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";
import LoadingState from "./LoadingState";

export default function ProtectedRoute({ children }) {
  const { isAuthenticated, checkingSession } = useAuth();

  if (checkingSession) {
    return <LoadingState fullPage label="Checking wallet session…" />;
  }

  if (!isAuthenticated) {
    return <Navigate to="/wallet" replace />;
  }

  return children;
}
