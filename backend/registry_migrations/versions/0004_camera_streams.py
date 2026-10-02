"""Store vendor camera stream endpoints."""
from alembic import op
import sqlalchemy as sa

revision = "0004_camera_streams"
down_revision = "0003_vendor_login"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("registry_cameras", sa.Column("stream_url", sa.String(2048), nullable=True))
    op.add_column("registry_cameras", sa.Column("stream_protocol", sa.String(20), nullable=True))


def downgrade():
    op.drop_column("registry_cameras", "stream_protocol")
    op.drop_column("registry_cameras", "stream_url")
