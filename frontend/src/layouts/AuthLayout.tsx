import { Link, Outlet } from "react-router-dom";

import { LogoMark } from "../components/icons";

export function AuthLayout() {
  return (
    <div className="min-h-screen bg-navy-950 text-ink">
      <div className="pointer-events-none fixed inset-0 bg-[radial-gradient(ellipse_at_top,_rgba(34,211,238,0.08),_transparent_55%)]" />
      <div className="relative mx-auto flex min-h-screen w-full max-w-md flex-col justify-center px-4 py-10">
        <Link to="/login" className="mb-8 flex items-center gap-3">
          <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-navy-900 text-cyan-300">
            <LogoMark className="h-5 w-5" />
          </span>
          <span>
            <span className="block text-sm font-semibold text-white">ReturnFlow</span>
            <span className="block text-xs text-ink-faint">Account access</span>
          </span>
        </Link>
        <Outlet />
      </div>
    </div>
  );
}
