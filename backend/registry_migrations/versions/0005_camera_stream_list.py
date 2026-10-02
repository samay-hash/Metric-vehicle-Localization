"""Allow several named stream endpoints per camera."""
from alembic import op
import sqlalchemy as sa

revision = "0005_camera_stream_list"
down_revision = "0004_camera_streams"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "registry_camera_streams",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("camera_id", sa.String(36), sa.ForeignKey("registry_cameras.id", ondelete="CASCADE"), nullable=False),
        sa.Column("label", sa.String(100), nullable=False),
        sa.Column("protocol", sa.String(20), nullable=False),
        sa.Column("url", sa.String(2048), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("camera_id", "position"),
    )
    op.create_index("ix_registry_camera_streams_camera", "registry_camera_streams", ["camera_id"])
    connection = op.get_bind()
    rows = connection.execute(sa.text(
        "SELECT id, stream_protocol, stream_url FROM registry_cameras WHERE stream_url IS NOT NULL"
    )).mappings()
    import uuid
    from datetime import datetime, timezone
    for row in rows:
        connection.execute(sa.text(
            "INSERT INTO registry_camera_streams (id, camera_id, label, protocol, url, position, created_at) "
            "VALUES (:id, :camera_id, :label, :protocol, :url, 0, :created_at)"
        ), {"id": str(uuid.uuid4()), "camera_id": row["id"], "label": "Main stream",
            "protocol": row["stream_protocol"], "url": row["stream_url"],
            "created_at": datetime.now(timezone.utc)})


def downgrade():
    op.drop_index("ix_registry_camera_streams_camera", table_name="registry_camera_streams")
    op.drop_table("registry_camera_streams")
