import { NavLink } from "react-router-dom";

import { useAuth } from "../hooks/useAuth";
import { ROLE_LABELS, hasPermission } from "../utils/access";
import { cn } from "../utils/cn";
import {
  ActivityIcon,
  BookIcon,
  ClipboardIcon,
  LayoutIcon,
  LogoMark,
  PackageIcon,
  ServerIcon,
  SettingsIcon,
  UsersIcon,
} from "./icons";

const items = [
  { to: "/", label: "Overview", icon: LayoutIcon, end: true, permission: "" },
  { to: "/activity", label: "Activity", icon: ActivityIcon, end: false, permission: "" },
  { to: "/orders", label: "Orders", icon: PackageIcon, end: false, permission: "orders" },
  { to: "/returns", label: "Returns", icon: ActivityIcon, end: false, permission: "returns" },
  { to: "/returns/queue", label: "Return queue", icon: ClipboardIcon, end: false, permission: "return:manage" },
  { to: "/knowledge", label: "Knowledge", icon: BookIcon, end: false, permission: "knowledge:read" },
  { to: "/policy", label: "Policy assistant", icon: BookIcon, end: false, permission: "knowledge:read" },
  { to: "/members", label: "Members", icon: UsersIcon, end: false, permission: "membership:read" },
  { to: "/audit", label: "Audit", icon: ClipboardIcon, end: false, permission: "audit:read" },
  { to: "/system", label: "System", icon: ServerIcon, end: false, permission: "" },
  { to: "/preferences", label: "Preferences", icon: SettingsIcon, end: false, permission: "" },
];

type SidebarProps = {
  open: boolean;
  isDesktop: boolean;
  onNavigate: () => void;
};

export function Sidebar({ open, isDesktop, onNavigate }: SidebarProps) {
  const { activeMembership, memberships, storeId, selectStore } = useAuth();
  const visible = items.filter((item) => {
    if (item.permission === "orders") {
      return (
        Boolean(storeId) &&
        (hasPermission(activeMembership?.permissions, "order:read") ||
          hasPermission(activeMembership?.permissions, "order:read_own"))
      );
    }
    if (item.permission === "returns") {
      return (
        Boolean(storeId) &&
        (hasPermission(activeMembership?.permissions, "return:read") ||
          hasPermission(activeMembership?.permissions, "return:read_own"))
      );
    }
    if (item.permission) {
      return Boolean(storeId) && hasPermission(activeMembership?.permissions, item.permission);
    }
    if (item.to === "/" || item.to === "/activity") {
      return Boolean(storeId);
    }
    return true;
  });

  return (
    <aside
      id="app-sidebar"
      data-testid="sidebar"
      inert={!isDesktop && !open ? true : undefined}
      className={cn(
        "fixed inset-y-0 left-0 z-40 flex w-72 flex-col border-r border-navy-600 bg-navy-900 transition-transform lg:static lg:z-auto lg:w-auto lg:translate-x-0",
        open ? "translate-x-0" : "-translate-x-full",
      )}
    >
      <div className="flex items-center gap-3 px-5 py-5">
        <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-navy-950 text-cyan-300">
          <LogoMark className="h-5 w-5" />
        </span>
        <div>
          <p className="text-sm font-semibold text-white">ReturnFlow</p>
          <p className="text-xs text-ink-faint">Returns platform</p>
        </div>
      </div>

      {memberships.length > 0 ? (
        <div className="px-5 pb-4">
          <label htmlFor="active-store" className="block text-xs font-medium uppercase tracking-wide text-ink-faint">
            Store
          </label>
          <select
            id="active-store"
            className="focus-ring mt-2 w-full rounded-lg border border-navy-600 bg-navy-950 px-3 py-2 text-sm text-ink"
            value={storeId ?? ""}
            onChange={(event) => selectStore(event.target.value)}
          >
            {storeId ? null : <option value="">Choose a store</option>}
            {memberships.map((membership) => (
              <option key={membership.store_id} value={membership.store_id}>
                {membership.store_name}
              </option>
            ))}
          </select>
        </div>
      ) : null}

      <nav className="flex-1 space-y-1 px-3" aria-label="Primary">
        {visible.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              onClick={onNavigate}
              className={({ isActive }) =>
                cn(
                  "focus-ring flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium",
                  isActive
                    ? "bg-cyan-400/10 text-cyan-200"
                    : "text-ink-muted hover:bg-navy-800 hover:text-ink",
                )
              }
            >
              <Icon className="h-4 w-4" />
              {item.label}
            </NavLink>
          );
        })}
        <NavLink
          to="/stores"
          onClick={onNavigate}
          className={({ isActive }) =>
            cn(
              "focus-ring flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium",
              isActive ? "bg-cyan-400/10 text-cyan-200" : "text-ink-muted hover:bg-navy-800 hover:text-ink",
            )
          }
        >
          All stores
        </NavLink>
      </nav>

      <div className="border-t border-navy-600 px-5 py-4">
        <p className="text-xs font-medium uppercase tracking-wide text-ink-faint">
          {activeMembership ? ROLE_LABELS[activeMembership.role] : "Account"}
        </p>
        <p className="mt-1 text-sm text-ink-muted">
          {activeMembership ? activeMembership.store_name : "Create or choose a store to continue."}
        </p>
      </div>
    </aside>
  );
}
