"""Create local dashboard RBAC accounts without resetting existing passwords."""
import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import select, text

from registry.auth import hash_password, normalize_email
from registry.config import Settings
from registry.db import make_engine, make_sessions
from registry.models import DashboardRoleAssignment, DashboardUser, SecurityAudit


ACCOUNTS = (
    ("admin@synetra.local", "Synetra Master Admin", "master_admin"),
    ("investigator@synetra.local", "Investigation Officer", "investigator"),
    ("maintenance@synetra.local", "Camera Maintenance", "maintenance"),
    ("it@synetra.local", "IT Operations", "it_operator"),
)


def main():
    load_dotenv(Path(__file__).resolve().parents[1] / ".env.registry")
    settings = Settings.from_env()
    password = os.getenv("REGISTRY_DASHBOARD_DEFAULT_PASSWORD", "")
    if not 12 <= len(password) <= 128:
        raise SystemExit("Set REGISTRY_DASHBOARD_DEFAULT_PASSWORD to 12–128 characters for local dashboard seeding")
    engine = make_engine(settings.database_url)
    sessions = make_sessions(engine)
    with engine.connect() as connection:
        if connection.execute(text("SELECT version_num FROM registry_alembic_version")).scalar() != "0007_dashboard_rbac":
            raise SystemExit("Run registry migrations before seeding dashboard accounts")
    results = []
    with sessions() as db:
        for email, display_name, role in ACCOUNTS:
            normalized = normalize_email(email)
            user = db.scalar(select(DashboardUser).where(DashboardUser.email == normalized))
            created = False
            if user is None:
                user = DashboardUser(email=normalized, display_name=display_name,
                                     password_hash=hash_password(password))
                db.add(user)
                db.flush()
                db.add(DashboardRoleAssignment(user_id=user.id, role=role, scope_type="global",
                                               scope_id="", created_by="seed-script"))
                db.add(SecurityAudit(actor="seed-script", action="dashboard_user.created",
                                     target_id=user.id, details={"email": normalized, "role": role}))
                created = True
            results.append((normalized, role, created))
        db.commit()
    engine.dispose()
    print("Dashboard accounts (all use REGISTRY_DASHBOARD_DEFAULT_PASSWORD):")
    for email, role, created in results:
        print(f"- {email} | {role} | {'created' if created else 'already existed'}")
    print("The plaintext password was not stored or printed. Re-running does not reset existing passwords.")


if __name__ == "__main__":
    main()
