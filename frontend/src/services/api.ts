import axios, { AxiosError, type InternalAxiosRequestConfig } from "axios";

import type { ErrorResponse } from "../types/api";
import { markSessionExpired, readStoreId, readToken } from "./session";

const viteApiBase = import.meta.env.VITE_API_BASE_URL;

/** Dev default is the API on :8000; Docker build passes an empty string for nginx same-origin proxy. */
export const apiBaseUrl = (() => {
  if (viteApiBase === undefined || viteApiBase === null) {
    return "http://localhost:8000";
  }
  const trimmed = String(viteApiBase).trim();
  if (trimmed === "") {
    return typeof window !== "undefined" ? window.location.origin : "http://localhost:8000";
  }
  return trimmed;
})();

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly requestId?: string;
  readonly details?: unknown;

  constructor(
    message: string,
    options: { status: number; code: string; requestId?: string; details?: unknown },
  ) {
    super(message);
    this.name = "ApiError";
    this.status = options.status;
    this.code = options.code;
    this.requestId = options.requestId;
    this.details = options.details;
  }
}

export const api = axios.create({
  baseURL: apiBaseUrl,
  timeout: 10000,
  headers: {
    Accept: "application/json",
  },
});

function authorizationHeader(config: InternalAxiosRequestConfig | undefined): string {
  if (!config?.headers) {
    return "";
  }
  const value = config.headers.get("Authorization");
  return typeof value === "string" ? value : "";
}

api.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const requestId = crypto.randomUUID();
  config.headers.set("X-Request-ID", requestId);
  config.requestId = requestId;
  const token = readToken();
  if (token) {
    config.headers.set("Authorization", `Bearer ${token}`);
  }
  const storeId = readStoreId();
  if (storeId) {
    config.headers.set("X-Store-ID", storeId);
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error: AxiosError<ErrorResponse>) => {
    if (axios.isCancel(error) || error.code === "ERR_CANCELED") {
      return Promise.reject(error);
    }

    const requestId = error.config?.requestId ?? error.response?.data?.request_id;
    const payload = error.response?.data?.error;
    const expired =
      Boolean(authorizationHeader(error.config)) &&
      error.response?.status === 401 &&
      (payload?.code === "token_expired" || payload?.code === "not_authenticated");
    if (expired) {
      markSessionExpired();
    }
    if (payload) {
      return Promise.reject(
        new ApiError(payload.message, {
          status: error.response?.status ?? 0,
          code: payload.code,
          requestId,
          details: payload.details,
        }),
      );
    }

    const unreachable = error.code === "ECONNABORTED" ? "The API timed out." : "The API is not reachable.";
    return Promise.reject(
      new ApiError(unreachable, {
        status: error.response?.status ?? 0,
        code: "network_error",
        requestId,
      }),
    );
  },
);
