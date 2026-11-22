import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from "react";

export type Density = "comfortable" | "compact";

export interface Preferences {
  displayName: string;
  email: string;
  density: Density;
  showSampleMetrics: boolean;
}

const defaultPreferences: Preferences = {
  displayName: "Operator",
  email: "",
  density: "comfortable",
  showSampleMetrics: true,
};

interface PreferencesContextValue extends Preferences {
  save: (next: Preferences) => void;
}

const PreferencesContext = createContext<PreferencesContextValue | null>(null);

export function PreferencesProvider({ children }: { children: ReactNode }) {
  const [preferences, setPreferences] = useState<Preferences>(defaultPreferences);
  const save = useCallback((next: Preferences) => {
    setPreferences(next);
  }, []);
  const value = useMemo(() => ({ ...preferences, save }), [preferences, save]);

  return <PreferencesContext.Provider value={value}>{children}</PreferencesContext.Provider>;
}

export function usePreferences(): PreferencesContextValue {
  const value = useContext(PreferencesContext);
  if (!value) {
    throw new Error("usePreferences must be used within PreferencesProvider");
  }
  return value;
}
