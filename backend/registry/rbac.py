"""Fixed RBAC policy and scope primitives shared by registry identities."""
from dataclasses import dataclass


ALL_PERMISSIONS = frozenset({
    "dashboard.access",
    "camera.read", "camera.health.read", "camera.metadata.write", "camera.technical.write",
    "camera.import", "camera.export", "camera.stream.view", "camera.stream.diagnose",
    "source.read", "source.write", "source.approve", "source.test", "source.sync",
    "event.read", "event.review", "event.ingest",
    "incident.read", "incident.write", "investigation.run",
    "evidence.read", "evidence.upload", "evidence.export",
    "report.read", "report.export", "topology.read", "topology.write",
    "vendor.read", "vendor.manage", "api_key.manage", "user.manage", "role.assign",
    "maintenance.manage", "system.read", "system.manage", "model.read", "model.promote",
    "audit.read",
})

ROLE_PERMISSIONS = {
    "master_admin": ALL_PERMISSIONS,
    "investigator": frozenset({
        "dashboard.access", "camera.read", "camera.health.read", "camera.stream.view",
        "event.read", "event.review", "incident.read", "incident.write", "investigation.run",
        "evidence.read", "evidence.upload", "evidence.export", "report.read", "report.export",
        "topology.read",
    }),
    "maintenance": frozenset({
        "dashboard.access", "camera.read", "camera.health.read", "camera.metadata.write",
        "camera.stream.diagnose", "source.read", "source.test", "source.sync",
        "topology.read", "maintenance.manage", "report.read",
    }),
    "it_operator": frozenset({
        "dashboard.access", "camera.read", "camera.health.read", "camera.technical.write",
        "camera.import", "camera.export", "camera.stream.view", "camera.stream.diagnose",
        "source.read", "source.write", "source.approve", "source.test", "source.sync", "event.ingest",
        "report.read", "report.export", "topology.read", "topology.write", "vendor.read",
        "api_key.manage", "system.read", "system.manage", "model.read", "model.promote",
        "audit.read",
    }),
    "vendor": frozenset({
        "camera.read", "camera.health.read", "camera.metadata.write", "camera.technical.write",
        "camera.import", "camera.export", "camera.stream.view", "camera.stream.diagnose",
        "source.read", "source.write", "source.test", "source.sync", "vendor.read",
        "api_key.manage", "audit.read",
    }),
    "service_reader": frozenset({
        "dashboard.access", "camera.read", "camera.health.read", "camera.stream.view",
        "source.read", "vendor.read", "topology.read", "event.read", "incident.read",
        "evidence.read", "report.read", "system.read", "model.read", "audit.read",
    }),
}

SYSTEM_ROLES = frozenset({"master_admin", "investigator", "maintenance", "it_operator"})
SCOPE_TYPES = frozenset({"global", "state", "district", "commissionerate", "zone", "police_station", "department", "vendor"})

ROLE_LANDING_PATHS = {
    "master_admin": "/dashboard",
    "investigator": "/dashboard/events",
    "maintenance": "/dashboard/maintenance",
    "it_operator": "/dashboard/topology",
    "vendor": "/vendor/onboarding",
}


@dataclass(frozen=True)
class Scope:
    type: str
    id: str | None = None

    def as_dict(self):
        return {"type": self.type, "id": self.id}


def permissions_for_roles(roles):
    permissions = set()
    for role in roles:
        permissions.update(ROLE_PERMISSIONS.get(role, ()))
    return frozenset(permissions)


def landing_path(roles):
    for role in ("master_admin", "investigator", "maintenance", "it_operator", "vendor"):
        if role in roles:
            return ROLE_LANDING_PATHS[role]
    return "/login"
