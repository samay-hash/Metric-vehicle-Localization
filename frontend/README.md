# Frontend

React + Vite, written in TypeScript. Use Node.js 22.12+ (22 LTS) or 24+.

```sh
npm ci
npm run dev
npm run typecheck
npm test
npm run build
```

`npm run build` checks types before bundling. Both application and tooling configs use strict checking. JavaScript source files are disabled.

- `src/main.tsx` is the browser entry point.
- `tsconfig.app.json` checks the application and its tests. `tsconfig.json` extends it for editor support.
- `tsconfig.node.json` checks `vite.config.ts` and `vitest.config.ts`.
- `src/types.ts` defines backend response contracts, request payloads, sessions, roles, and permissions. Update these alongside backend changes.
- `src/env.d.ts` declares supported Vite environment variables.
- `src/api.ts` preserves the existing endpoint conventions: analytics helpers return Axios responses (`response.data`); registry helpers return parsed JSON directly.

HTTP response types describe the expected backend contract; they do not validate arbitrary JSON at runtime. Stored sessions are validated before use. Bulk camera imports intentionally accept `unknown[]` because the registry's preview endpoint validates each submitted row before import.

Local API defaults follow the browser's hostname (`localhost` or `127.0.0.1`), using port 8000 for analytics and 8001 for the registry. Stream images send the HTTP-only login cookie with `crossOrigin="use-credentials"`. Keep the frontend, registry and stream endpoints on the same site; changing between local hostnames requires signing in again. Override endpoints with `VITE_ANALYTICS_API_URL` and `VITE_REGISTRY_API_URL` when needed, with matching credentialed CORS settings on the servers.

Tests cover malformed/expired sessions, dashboard/vendor session separation, authenticated request headers, camera revision headers, registry failures and empty responses, and nullable map coordinates. Keep new application code in `.ts`/`.tsx`; use explicit domain types and narrow `unknown` at external boundaries instead of suppressing compiler errors.
