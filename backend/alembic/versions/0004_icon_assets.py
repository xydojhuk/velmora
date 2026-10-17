from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0004_icon_assets"
down_revision = "0003_store_operations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "icon_assets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("key", sa.String(80), nullable=False),
        sa.Column("label", sa.String(120), nullable=False),
        sa.Column("svg_markup", sa.Text(), nullable=False),
        sa.Column("original_name", sa.String(255), nullable=False, server_default=""),
        sa.Column("size_bytes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("updated_by_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("key", name="uq_icon_assets_key"),
        sa.CheckConstraint("size_bytes >= 0", name="ck_icon_assets_size_nonnegative"),
    )
    op.create_index("ix_icon_assets_key", "icon_assets", ["key"])


def downgrade() -> None:
    op.drop_index("ix_icon_assets_key", table_name="icon_assets")
    op.drop_table("icon_assets")
