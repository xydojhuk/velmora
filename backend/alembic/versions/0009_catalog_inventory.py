"""Add opt-in stock management and category label.

Revision ID: 0009_catalog_inventory
Revises: 0008_storefront_builder
"""
from alembic import op
import sqlalchemy as sa

revision = "0009_catalog_inventory"
down_revision = "0008_storefront_builder"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("products", sa.Column("category_slug", sa.String(80), nullable=False, server_default="general"))
    op.add_column("products", sa.Column("track_inventory", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("products", sa.Column("stock_quantity", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("products", sa.Column("low_stock_threshold", sa.Integer(), nullable=False, server_default="5"))
    op.create_index("ix_products_category_slug", "products", ["category_slug"])
    op.create_check_constraint("ck_products_stock_nonnegative", "products", "stock_quantity >= 0")
    op.create_check_constraint("ck_products_threshold_nonnegative", "products", "low_stock_threshold >= 0")


def downgrade():
    op.drop_constraint("ck_products_threshold_nonnegative", "products", type_="check")
    op.drop_constraint("ck_products_stock_nonnegative", "products", type_="check")
    op.drop_index("ix_products_category_slug", table_name="products")
    for name in ("low_stock_threshold", "stock_quantity", "track_inventory", "category_slug"):
        op.drop_column("products", name)
