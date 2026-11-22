import { Navigate, Outlet, useLocation } from "react-router-dom";

import { useAuth } from "../hooks/useAuth";
import { Spinner } from "./ui/Spinner";

function CheckingSession() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-navy-950">
      <Spinner label="Checking your session" />
    </div>
  );
}

export function GuestOnly() {
  const { status, memberships, storeId } = useAuth();
  if (status === "loading") {
    return <CheckingSession />;
  }
  if (status === "authenticated") {
    if (memberships.length === 0) {
      return <Navigate to="/onboarding" replace />;
    }
    if (!storeId) {
      return <Navigate to="/stores" replace />;
    }
    return <Navigate to="/" replace />;
  }
  return <Outlet />;
}

export function RequireAuth() {
  const { status } = useAuth();
  const location = useLocation();
  if (status === "loading") {
    return <CheckingSession />;
  }
  if (status !== "authenticated") {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }
  return <Outlet />;
}

export function RequireStore() {
  const { memberships, storeId } = useAuth();
  if (memberships.length === 0) {
    return <Navigate to="/onboarding" replace />;
  }
  if (!storeId) {
    return <Navigate to="/stores" replace />;
  }
  return <Outlet />;
}
