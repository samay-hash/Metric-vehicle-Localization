"""Add dashboard identities, scoped role assignments and security audit."""
from alembic import op
import sqlalchemy as sa

revision = "0007_dashboard_rbac"
down_revision = "0006_camera_health"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "registry_dashboard_users",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("email", sa.String(320), nullable=False, unique=True),
        sa.Column("display_name", sa.String(200), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "registry_dashboard_role_assignments",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("registry_dashboard_users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.String(40), nullable=False),
        sa.Column("scope_type", sa.String(40), nullable=False),
        sa.Column("scope_id", sa.String(200), nullable=False, server_default=""),
        sa.Column("created_by", sa.String(100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("user_id", "role", "scope_type", "scope_id"),
    )
    op.create_index("ix_registry_dashboard_role_assignments_user_id", "registry_dashboard_role_assignments", ["user_id"])
    op.create_index("ix_registry_dashboard_role_assignments_role", "registry_dashboard_role_assignments", ["role"])
    op.create_index("ix_registry_dashboard_role_assignments_scope_type", "registry_dashboard_role_assignments", ["scope_type"])
    op.create_table(
        "registry_dashboard_sessions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("registry_dashboard_users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token_digest", sa.String(64), nullable=False, unique=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_registry_dashboard_sessions_user_id", "registry_dashboard_sessions", ["user_id"])
    op.create_index("ix_registry_dashboard_sessions_expires_at", "registry_dashboard_sessions", ["expires_at"])
    op.create_table(
        "registry_security_audit",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("actor", sa.String(100), nullable=False),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("target_id", sa.String(100)),
        sa.Column("details", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_registry_security_audit_actor", "registry_security_audit", ["actor"])
    op.create_index("ix_registry_security_audit_action", "registry_security_audit", ["action"])
    op.create_index("ix_registry_security_audit_target_id", "registry_security_audit", ["target_id"])
    op.create_index("ix_registry_security_audit_created_at", "registry_security_audit", ["created_at"])


def downgrade():
    op.drop_table("registry_security_audit")
    op.drop_table("registry_dashboard_sessions")
    op.drop_table("registry_dashboard_role_assignments")
    op.drop_table("registry_dashboard_users")
