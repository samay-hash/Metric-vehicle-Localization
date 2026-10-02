/// <reference types="vite/client" />

interface ViteTypeOptions {
  strictImportMetaEnv: unknown;
}

interface ImportMetaEnv {
  readonly VITE_ANALYTICS_API_URL?: string;
  readonly VITE_REGISTRY_API_URL?: string;
}
