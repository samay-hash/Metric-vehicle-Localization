"""Create five local demo vendor logins. Safe to repeat without resetting passwords."""
import os
import secrets
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import func, select, text

from registry.auth import hash_password, normalize_email
from registry.config import Settings
from registry.db import make_engine, make_sessions
from registry.models import Audit, Camera, Source, Vendor, VendorUser

PREFIXES = ("Apex", "Civic", "Harbor", "Nexus", "Orbit", "Pioneer", "Sterling", "Unity")
SUFFIXES = ("Vision", "Secure", "Surveillance", "Networks", "Systems", "Monitoring")


def generated_name():
    return f"{secrets.choice(PREFIXES)} {secrets.choice(SUFFIXES)} {secrets.randbelow(900) + 100}"


def main():
    load_dotenv(Path(__file__).resolve().parents[1] / ".env.registry")
    settings = Settings.from_env()
    password = os.getenv("REGISTRY_VENDOR_DEFAULT_PASSWORD", "")
    if not 12 <= len(password) <= 128:
        raise SystemExit("Set REGISTRY_VENDOR_DEFAULT_PASSWORD to 12–128 characters for the local seed operation")
    engine = make_engine(settings.database_url)
    sessions = make_sessions(engine)
    with engine.connect() as connection:
        if connection.execute(text("SELECT version_num FROM registry_alembic_version")).scalar() != "0005_camera_stream_list":
            raise SystemExit("Run registry migrations before seeding vendor accounts")

    specs = [
        ("sentinel.vendor@synetra.local", "Sentinel Vendor Operator", "sentinel", "Sentinel"),
        ("vendor2@synetra.local", "Vendor Operator 2", "demo-vendor-2", None),
        ("vendor3@synetra.local", "Vendor Operator 3", "demo-vendor-3", None),
        ("vendor4@synetra.local", "Vendor Operator 4", "demo-vendor-4", None),
        ("vendor5@synetra.local", "Vendor Operator 5", "demo-vendor-5", None),
    ]
    output = []
    with sessions() as db:
        sentinel = db.scalar(select(Vendor).where(Vendor.slug == "sentinel"))
        if sentinel is None:
            raise SystemExit("Run scripts/bootstrap_registry.py first so the Sentinel account can own the imported cameras")
        for email, display_name, vendor_slug, fixed_name in specs:
            vendor = db.scalar(select(Vendor).where(Vendor.slug == vendor_slug))
            created_vendor = False
            if vendor is None:
                vendor = Vendor(slug=vendor_slug, name=fixed_name or generated_name())
                db.add(vendor)
                db.flush()
                created_vendor = True
            normalized = normalize_email(email)
            user = db.scalar(select(VendorUser).where(VendorUser.email == normalized))
            created_user = False
            if user is None:
                user = VendorUser(vendor_id=vendor.id, email=normalized, display_name=display_name,
                                  password_hash=hash_password(password))
                db.add(user)
                db.flush()
                db.add(Audit(vendor_id=vendor.id, resource_id=user.id, actor="seed-script",
                             action="vendor_user.created", changes={"email": normalized, "display_name": display_name}))
                created_user = True
            elif user.vendor_id != vendor.id:
                raise SystemExit(f"Existing account {normalized} belongs to a different vendor; no changes were made")
            camera_count = db.scalar(select(func.count()).select_from(Camera).join(Source).where(Source.vendor_id == vendor.id))
            output.append((normalized, vendor.name, camera_count, created_vendor, created_user))
        db.commit()
    engine.dispose()
    print("Vendor accounts (all use REGISTRY_VENDOR_DEFAULT_PASSWORD):")
    for email, vendor_name, camera_count, created_vendor, created_user in output:
        state = "created" if created_user else "already existed"
        print(f"- {email} | {vendor_name} | cameras={camera_count} | {state}")
    print("The plaintext password was not stored or printed. Re-running does not reset existing passwords.")


if __name__ == "__main__":
    main()
