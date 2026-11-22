import { useCallback, useState } from "react";
import { Link } from "react-router-dom";

import { useAuth } from "../hooks/useAuth";
import { useDismiss } from "../hooks/useDismiss";
import { usePlatformStatus } from "../hooks/usePlatformStatus";
import { ApiError } from "../services/api";
import { ROLE_LABELS } from "../utils/access";
import { cn } from "../utils/cn";
import { formatDateTime, initials } from "../utils/format";
import { BellIcon, CloseIcon, MenuIcon } from "./icons";
import { EmptyState } from "./ui/EmptyState";

type TopNavProps = {
  title: string;
  sidebarOpen: boolean;
  onMenu: () => void;
};

const statusCopy = {
  loading: "Checking status",
  success: "Dependencies reachable",
  degraded: "Dependency unavailable",
  error: "API unavailable",
} as const;

const statusColor = {
  loading: "bg-cyan-300",
  success: "bg-emerald-400",
  degraded: "bg-amber-300",
  error: "bg-rose-400",
} as const;

export function TopNav({ title, sidebarOpen, onMenu }: TopNavProps) {
  const { status } = usePlatformStatus();
  const { user, activeMembership, signOut } = useAuth();
  const displayName = user?.display_name || "Account";
  const [notificationsOpen, setNotificationsOpen] = useState(false);
  const [profileOpen, setProfileOpen] = useState(false);
  const [signOutError, setSignOutError] = useState("");
  const closeNotifications = useCallback(() => setNotificationsOpen(false), []);
  const closeProfile = useCallback(() => setProfileOpen(false), []);
  const notificationRef = useDismiss<HTMLDivElement>(notificationsOpen, closeNotifications);
  const profileRef = useDismiss<HTMLDivElement>(profileOpen, closeProfile);
  const localTime = formatDateTime(new Date());

  return (
    <header className="sticky top-0 z-20 flex h-16 items-center gap-3 border-b border-navy-600 bg-navy-950/90 px-4 backdrop-blur sm:px-6">
      <button
        type="button"
        className="focus-ring rounded-lg p-2 text-ink lg:hidden"
        aria-controls="app-sidebar"
        aria-expanded={sidebarOpen}
        data-testid="menu-button"
        onClick={onMenu}
      >
        {sidebarOpen ? <CloseIcon className="h-5 w-5" /> : <MenuIcon className="h-5 w-5" />}
        <span className="sr-only">{sidebarOpen ? "Close navigation" : "Open navigation"}</span>
      </button>

      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-semibold text-white">{title}</p>
        <p className="hidden text-xs text-ink-faint sm:block">Local time {localTime}</p>
      </div>

      <p className="hidden items-center gap-2 text-xs text-ink-muted md:flex">
        <span className={cn("h-2 w-2 rounded-full", statusColor[status.phase])} aria-hidden="true" />
        <span>{statusCopy[status.phase]}</span>
      </p>

      <div className="relative" ref={notificationRef}>
        <button
          type="button"
          className="focus-ring rounded-lg p-2 text-ink-muted hover:bg-navy-800 hover:text-ink"
          aria-expanded={notificationsOpen}
          aria-controls="notification-panel"
          aria-label="Notifications, none"
          onClick={() => {
            setProfileOpen(false);
            setNotificationsOpen((open) => !open);
          }}
        >
          <BellIcon className="h-5 w-5" />
        </button>
        {notificationsOpen ? (
          <div
            id="notification-panel"
            className="absolute right-0 mt-2 w-80 rounded-2xl border border-navy-600 bg-navy-900 p-3 shadow-panel"
          >
            <p className="px-2 pb-2 text-sm font-semibold text-white">Notifications</p>
            <EmptyState
              title="No operational alerts"
              description="Return, refund, and carrier events are not produced in this phase."
            />
          </div>
        ) : null}
      </div>

      <div className="relative" ref={profileRef}>
        <button
          type="button"
          className="focus-ring flex items-center gap-2 rounded-full py-1 pl-1 pr-2 hover:bg-navy-800"
          aria-expanded={profileOpen}
          aria-controls="profile-menu"
          aria-label={`Account, ${displayName}`}
          onClick={() => {
            setNotificationsOpen(false);
            setProfileOpen((open) => !open);
          }}
        >
          <span className="flex h-8 w-8 items-center justify-center rounded-full bg-cyan-400 font-mono text-xs font-medium text-navy-950">
            {initials(displayName)}
          </span>
          <span className="hidden text-left sm:block">
            <span className="block text-sm font-medium leading-4 text-white">{displayName}</span>
            <span className="block text-[11px] text-ink-faint">
              {activeMembership ? ROLE_LABELS[activeMembership.role] : "Account"}
            </span>
          </span>
        </button>
        {profileOpen ? (
          <div
            id="profile-menu"
            role="menu"
            className="absolute right-0 mt-2 w-64 rounded-2xl border border-navy-600 bg-navy-900 p-2 shadow-panel"
          >
            <Link
              role="menuitem"
              to="/profile"
              className="focus-ring block rounded-lg px-3 py-2 text-sm text-ink hover:bg-navy-800"
              onClick={closeProfile}
            >
              Profile
            </Link>
            <Link
              role="menuitem"
              to="/preferences"
              className="focus-ring block rounded-lg px-3 py-2 text-sm text-ink hover:bg-navy-800"
              onClick={closeProfile}
            >
              Display preferences
            </Link>
            <button
              type="button"
              role="menuitem"
              className="focus-ring block w-full rounded-lg px-3 py-2 text-left text-sm text-ink hover:bg-navy-800"
              onClick={() => {
                setSignOutError("");
                signOut()
                  .then(closeProfile)
                  .catch((error: unknown) => {
                    setSignOutError(error instanceof ApiError ? error.message : "Sign-out failed.");
                  });
              }}
            >
              Sign out
            </button>
            {signOutError ? <p className="px-3 py-2 text-xs leading-5 text-rose-300">{signOutError}</p> : null}
          </div>
        ) : null}
      </div>
    </header>
  );
}
