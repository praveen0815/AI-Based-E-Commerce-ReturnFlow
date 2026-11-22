import axios from "axios";
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import { ApiError } from "../services/api";
import { getHealth, getReadiness } from "../services/health";
import type { HealthData, ReadinessData } from "../types/health";

export type PlatformStatus =
  | { phase: "loading" }
  | { phase: "error"; message: string; requestId?: string }
  | { phase: "degraded"; health: HealthData; readiness: ReadinessData }
  | { phase: "success"; health: HealthData; readiness: ReadinessData };

interface PlatformStatusContextValue {
  status: PlatformStatus;
  reload: () => void;
}

const PlatformStatusContext = createContext<PlatformStatusContextValue | null>(null);

function isAbort(error: unknown): boolean {
  return axios.isCancel(error) || (axios.isAxiosError(error) && error.code === "ERR_CANCELED");
}

function usePlatformStatusController(): PlatformStatusContextValue {
  const [status, setStatus] = useState<PlatformStatus>({ phase: "loading" });
  const [reloadKey, setReloadKey] = useState(0);
  const reload = useCallback(() => setReloadKey((value) => value + 1), []);

  useEffect(() => {
    const controller = new AbortController();
    let active = true;
    setStatus({ phase: "loading" });

    async function load() {
      try {
        const health = await getHealth(controller.signal);
        const readiness = await getReadiness(controller.signal);
        if (!active) {
          return;
        }
        setStatus({
          phase: readiness.status === "ready" ? "success" : "degraded",
          health,
          readiness,
        });
      } catch (error) {
        if (!active || isAbort(error)) {
          return;
        }
        if (error instanceof ApiError) {
          setStatus({ phase: "error", message: error.message, requestId: error.requestId });
          return;
        }
        setStatus({ phase: "error", message: "The platform status could not be loaded." });
      }
    }

    void load();
    return () => {
      active = false;
      controller.abort();
    };
  }, [reloadKey]);

  return useMemo(() => ({ status, reload }), [status, reload]);
}

export function PlatformStatusProvider({ children }: { children: ReactNode }) {
  const value = usePlatformStatusController();
  return <PlatformStatusContext.Provider value={value}>{children}</PlatformStatusContext.Provider>;
}

export function usePlatformStatus(): PlatformStatusContextValue {
  const value = useContext(PlatformStatusContext);
  if (!value) {
    throw new Error("usePlatformStatus must be used within PlatformStatusProvider");
  }
  return value;
}
