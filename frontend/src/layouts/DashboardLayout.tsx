import { useState } from "react";
import { Outlet, useLocation } from "react-router-dom";

import { Sidebar } from "../components/Sidebar";
import { TopNav } from "../components/TopNav";
import { useMediaQuery } from "../hooks/useMediaQuery";
import { PlatformStatusProvider } from "../hooks/usePlatformStatus";

const titles: Record<string, string> = {
  "/": "Overview",
  "/activity": "Activity",
  "/orders": "Orders",
  "/returns": "Returns",
  "/returns/queue": "Return queue",
  "/members": "Members",
  "/audit": "Audit",
  "/system": "System",
  "/preferences": "Preferences",
  "/profile": "Profile",
  "/onboarding": "Create a store",
  "/stores": "Stores",
};

export function DashboardLayout() {
  const location = useLocation();
  const isDesktop = useMediaQuery("(min-width: 1024px)");
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const title = titles[location.pathname] ?? "ReturnFlow";

  return (
    <PlatformStatusProvider>
      <div className="relative min-h-screen bg-navy-950 text-ink">
        <div className="pointer-events-none fixed inset-0 bg-[radial-gradient(ellipse_at_top,_rgba(34,211,238,0.08),_transparent_55%)]" />
        <a
          href="#main"
          className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:rounded-md focus:bg-cyan-400 focus:px-3 focus:py-2 focus:text-sm focus:font-semibold focus:text-navy-950"
        >
          Skip to content
        </a>
        {sidebarOpen ? (
          <button
            type="button"
            className="fixed inset-0 z-30 bg-black/60 lg:hidden"
            aria-label="Close navigation"
            onClick={() => setSidebarOpen(false)}
          />
        ) : null}
        <div className="relative lg:grid lg:min-h-screen lg:grid-cols-[18rem_minmax(0,1fr)]">
          <Sidebar
            open={sidebarOpen}
            isDesktop={isDesktop}
            onNavigate={() => {
              if (!isDesktop) {
                setSidebarOpen(false);
              }
            }}
          />
          <div className="min-w-0">
            <TopNav
              title={title}
              sidebarOpen={sidebarOpen}
              onMenu={() => setSidebarOpen((open) => !open)}
            />
            <main id="main" className="mx-auto w-full max-w-7xl px-4 py-6 sm:px-6 lg:px-8 lg:py-8">
              <Outlet />
            </main>
          </div>
        </div>
      </div>
    </PlatformStatusProvider>
  );
}
