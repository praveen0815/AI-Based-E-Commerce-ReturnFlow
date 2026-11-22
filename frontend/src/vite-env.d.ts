/// <reference types="vite/client" />

declare module "axios" {
  export interface AxiosRequestConfig {
    requestId?: string;
  }

  export interface InternalAxiosRequestConfig {
    requestId?: string;
  }
}

declare global {
  interface ImportMetaEnv {
    readonly VITE_API_BASE_URL?: string;
  }
}

export {};
