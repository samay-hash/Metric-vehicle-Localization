"""Add simple database-backed vendor accounts and revocable login sessions."""
from alembic import op
import sqlalchemy as sa

revision = "0003_vendor_login"
down_revision = "0002_camera_department"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "registry_vendor_users",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("vendor_id", sa.String(36), nullable=False),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("display_name", sa.String(200), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["vendor_id"], ["registry_vendors.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_index("ix_registry_vendor_users_vendor_id", "registry_vendor_users", ["vendor_id"])
    op.create_table(
        "registry_vendor_sessions",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("token_digest", sa.String(64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["registry_vendor_users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_digest"),
    )
    op.create_index("ix_registry_vendor_sessions_user_id", "registry_vendor_sessions", ["user_id"])
    op.create_index("ix_registry_vendor_sessions_expires_at", "registry_vendor_sessions", ["expires_at"])


def downgrade():
    op.drop_index("ix_registry_vendor_sessions_expires_at", table_name="registry_vendor_sessions")
    op.drop_index("ix_registry_vendor_sessions_user_id", table_name="registry_vendor_sessions")
    op.drop_table("registry_vendor_sessions")
    op.drop_index("ix_registry_vendor_users_vendor_id", table_name="registry_vendor_users")
    op.drop_table("registry_vendor_users")
