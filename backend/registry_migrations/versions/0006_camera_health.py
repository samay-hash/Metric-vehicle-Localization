"""Persist camera probe observations independently of catalogue metadata."""
from alembic import op
import sqlalchemy as sa

revision = "0006_camera_health"
down_revision = "0005_camera_stream_list"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("registry_cameras", sa.Column("health_generation", sa.Integer(), nullable=False, server_default="1"))
    op.add_column("registry_sources", sa.Column("health_generation", sa.Integer(), nullable=False, server_default="1"))
    op.create_table(
        "registry_camera_health",
        sa.Column("camera_id", sa.String(36), sa.ForeignKey("registry_cameras.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("stream_key", sa.String(100), nullable=False),
        sa.Column("target_revision", sa.String(64), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("candidate", sa.String(30), nullable=False),
        sa.Column("consecutive_count", sa.Integer(), nullable=False),
        sa.Column("checked_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_frame_at", sa.DateTime(timezone=True)),
        sa.Column("details", sa.JSON(), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
    )
    op.create_index("ix_registry_camera_health_expires_at", "registry_camera_health", ["expires_at"])
    op.create_table(
        "registry_health_measurements",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("camera_id", sa.String(36), sa.ForeignKey("registry_cameras.id", ondelete="CASCADE"), nullable=False),
        sa.Column("stream_key", sa.String(100), nullable=False),
        sa.Column("target_revision", sa.String(64), nullable=False),
        sa.Column("checked_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("connectivity", sa.String(30), nullable=False),
        sa.Column("previous_status", sa.String(30)),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("details", sa.JSON(), nullable=False),
    )
    op.create_index("ix_health_measurements_camera_time", "registry_health_measurements", ["camera_id", "checked_at"])
    op.create_index("ix_registry_health_measurements_checked_at", "registry_health_measurements", ["checked_at"])


def downgrade():
    op.drop_table("registry_health_measurements")
    op.drop_table("registry_camera_health")
    op.drop_column("registry_cameras", "health_generation")
    op.drop_column("registry_sources", "health_generation")
