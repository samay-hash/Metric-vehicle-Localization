# Dashboard role-based access control

The registry API is the identity and authorization authority for the Synetra dashboard. It issues opaque dashboard sessions, resolves role assignments into permissions, applies data scopes to registry queries, and records security-sensitive activity. The analytics API validates the same session through the registry before serving protected routes.

## Roles

| Role | Primary responsibilities | Key access |
| --- | --- | --- |
| Master Admin | Platform ownership and access administration | All permissions, users, roles, configuration, audit |
| Investigator / Security | Review events and build cases | Events, live feeds, incidents, investigation, evidence, reports |
| Maintenance | Keep cameras operational | Scoped camera inventory, health, diagnostics, metadata, source tests and sync |
| IT Operator | Operate integrations and infrastructure | Sources, approvals, camera configuration, imports, topology, system and model controls, audit |
| Vendor | Maintain only its own integration and cameras | Vendor-scoped sources, cameras, streams, health, imports, API keys and audit |

Roles are fixed policy bundles in `backend/registry/rbac.py`. Database assignments bind one or more roles to a scope. A user receives the union of their role permissions, while all registry reads remain limited to the assigned scope.

## Scopes

`global`, `vendor`, and `department` scopes are enforced by current registry queries. A camera-level department overrides its source department. The schema also reserves `state`, `district`, `commissionerate`, `zone`, and `police_station`; these deny registry rows until those jurisdiction fields are added to the normalized camera catalogue. Analytics records do not yet carry normalized jurisdiction IDs, so non-global identities are denied direct analytics routes and WebSocket events; they can still use registry-backed camera and health screens. This secure default prevents an unsupported scope from accidentally becoming global access.

## Enforcement flow

1. `POST /api/v1/auth/login` verifies a dashboard account and creates a revocable opaque session.
2. `GET /api/v1/me` returns the current roles, permissions, scopes, and role landing page.
3. Registry endpoints require a named permission and apply scope filters in SQL.
4. The analytics middleware introspects the session with the registry and checks a permission for every protected route.
5. The React router and sidebar use the returned permissions to present only usable views. This is a usability layer; backend checks remain authoritative.
6. Role replacement revokes all active sessions so permission changes take effect immediately.

The dashboard session is available as an `HttpOnly`, `SameSite=Lax` cookie and as a bearer token for the existing cross-port local development setup. Production should serve both APIs behind one HTTPS origin and rely on the secure cookie.

## Local setup

Set a local seed password with at least 12 characters:

```sh
REGISTRY_DASHBOARD_DEFAULT_PASSWORD='choose-a-local-password' make registry-migrate registry-seed-rbac
```

The seed creates these idempotent global accounts:

- `admin@synetra.local`
- `investigator@synetra.local`
- `maintenance@synetra.local`
- `it@synetra.local`

Change the seed password outside local development and create individually scoped accounts through **Access management**. The seed script never stores the plaintext password.

## Audit

`GET /api/v1/access/audit` exposes recent authentication, account, and role-assignment events to identities with `audit.read`. Audit details include identifiers and assignment metadata and never include submitted passwords or raw session tokens.
