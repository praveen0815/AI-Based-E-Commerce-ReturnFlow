const TOKEN_KEY = "returnflow.access_token";
const STORE_KEY = "returnflow.store_id";

export const SESSION_EXPIRED_EVENT = "returnflow:session-expired";

export function readToken(): string | null {
  return sessionStorage.getItem(TOKEN_KEY);
}

export function readStoreId(): string | null {
  return sessionStorage.getItem(STORE_KEY);
}

export function saveToken(token: string): void {
  sessionStorage.setItem(TOKEN_KEY, token);
}

export function saveStoreId(storeId: string): void {
  sessionStorage.setItem(STORE_KEY, storeId);
}

export function clearSession(): void {
  sessionStorage.removeItem(TOKEN_KEY);
  sessionStorage.removeItem(STORE_KEY);
}

export function markSessionExpired(): void {
  clearSession();
  window.dispatchEvent(new Event(SESSION_EXPIRED_EVENT));
}
