import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";

import { ApiError } from "../services/api";
import { currentUser, loginAccount, logoutAccount, registerAccount } from "../services/auth";
import {
  SESSION_EXPIRED_EVENT,
  clearSession,
  readStoreId,
  readToken,
  saveStoreId,
  saveToken,
} from "../services/session";
import type { AuthUser, Membership } from "../types/auth";

type Status = "loading" | "anonymous" | "authenticated";

interface AuthContextValue {
  status: Status;
  user: AuthUser | null;
  memberships: Membership[];
  storeId: string | null;
  activeMembership: Membership | null;
  sessionExpired: boolean;
  signIn: (email: string, password: string) => Promise<void>;
  signUp: (email: string, password: string, displayName: string) => Promise<void>;
  signOut: () => Promise<void>;
  refresh: () => Promise<void>;
  selectStore: (storeId: string) => void;
  clearSessionNotice: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

function chooseStore(memberships: Membership[], preferred: string | null): string | null {
  if (preferred && memberships.some((item) => item.store_id === preferred)) {
    return preferred;
  }
  if (memberships.length === 1) {
    return memberships[0].store_id;
  }
  return null;
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<Status>(readToken() ? "loading" : "anonymous");
  const [user, setUser] = useState<AuthUser | null>(null);
  const [memberships, setMemberships] = useState<Membership[]>([]);
  const [storeId, setStoreId] = useState<string | null>(readStoreId());
  const [sessionExpired, setSessionExpired] = useState(false);

  const applyCurrent = useCallback((nextUser: AuthUser, nextMemberships: Membership[]) => {
    const selected = chooseStore(nextMemberships, readStoreId());
    if (selected) {
      saveStoreId(selected);
    }
    setUser(nextUser);
    setMemberships(nextMemberships);
    setStoreId(selected);
    setStatus("authenticated");
  }, []);

  const refresh = useCallback(async () => {
    const me = await currentUser();
    applyCurrent(me.user, me.memberships);
  }, [applyCurrent]);

  useEffect(() => {
    const onExpired = () => {
      setUser(null);
      setMemberships([]);
      setStoreId(null);
      setStatus("anonymous");
      setSessionExpired(true);
    };
    window.addEventListener(SESSION_EXPIRED_EVENT, onExpired);
    return () => window.removeEventListener(SESSION_EXPIRED_EVENT, onExpired);
  }, []);

  useEffect(() => {
    if (!readToken()) {
      setStatus("anonymous");
      return;
    }
    let cancelled = false;
    currentUser()
      .then((me) => {
        if (!cancelled) {
          applyCurrent(me.user, me.memberships);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setStatus("anonymous");
        }
      });
    return () => {
      cancelled = true;
    };
  }, [applyCurrent]);

  const signIn = useCallback(
    async (email: string, password: string) => {
      const result = await loginAccount({ email, password });
      saveToken(result.token.access_token);
      setSessionExpired(false);
      await refresh();
    },
    [refresh],
  );

  const signUp = useCallback(
    async (email: string, password: string, displayName: string) => {
      const result = await registerAccount({
        email,
        password,
        display_name: displayName,
      });
      saveToken(result.token.access_token);
      setSessionExpired(false);
      await refresh();
    },
    [refresh],
  );

  const signOut = useCallback(async () => {
    try {
      await logoutAccount();
    } catch (error) {
      const expired =
        error instanceof ApiError && (error.code === "token_expired" || error.code === "not_authenticated");
      if (!expired) {
        throw error;
      }
    }
    clearSession();
    setUser(null);
    setMemberships([]);
    setStoreId(null);
    setSessionExpired(false);
    setStatus("anonymous");
  }, []);

  const selectStore = useCallback((nextStoreId: string) => {
    saveStoreId(nextStoreId);
    setStoreId(nextStoreId);
  }, []);

  const clearSessionNotice = useCallback(() => setSessionExpired(false), []);

  const activeMembership = memberships.find((item) => item.store_id === storeId) ?? null;

  const value = useMemo<AuthContextValue>(
    () => ({
      status,
      user,
      memberships,
      storeId,
      activeMembership,
      sessionExpired,
      signIn,
      signUp,
      signOut,
      refresh,
      selectStore,
      clearSessionNotice,
    }),
    [
      status,
      user,
      memberships,
      storeId,
      activeMembership,
      sessionExpired,
      signIn,
      signUp,
      signOut,
      refresh,
      selectStore,
      clearSessionNotice,
    ],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const value = useContext(AuthContext);
  if (!value) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return value;
}
