"""Allow a vendor catalogue to contain cameras owned by different departments."""
from alembic import op
import sqlalchemy as sa

revision = "0002_camera_department"
down_revision = "0001_registry"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("registry_cameras", sa.Column("department", sa.String(200), nullable=True))
    op.create_index("ix_registry_cameras_department", "registry_cameras", ["department"])


def downgrade():
    op.drop_index("ix_registry_cameras_department", table_name="registry_cameras")
    op.drop_column("registry_cameras", "department")
