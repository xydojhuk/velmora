"""Create managed categories; protect idempotent public order submissions.

Revision ID: 0010_categories_and_idempotency
Revises: 0009_catalog_inventory
"""
from alembic import op
import sqlalchemy as sa

revision = "0010_categories_and_idempotency"
down_revision = "0009_catalog_inventory"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "categories",
        sa.Column("slug", sa.String(80), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.String(500), nullable=False, server_default=""),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    # Existing category slugs are retained and made manageable without losing products.
    op.execute(sa.text("""
        INSERT INTO categories(slug, name)
        SELECT DISTINCT category_slug, initcap(replace(category_slug, '-', ' '))
        FROM products WHERE category_slug IS NOT NULL
        ON CONFLICT (slug) DO NOTHING
    """))
    op.execute(sa.text("INSERT INTO categories(slug, name) VALUES ('general', 'General') ON CONFLICT (slug) DO NOTHING"))
    op.create_foreign_key("fk_products_category_slug", "products", "categories", ["category_slug"], ["slug"], ondelete="RESTRICT")
    op.add_column("orders", sa.Column("idempotency_fingerprint", sa.String(64), nullable=True))


def downgrade():
    op.drop_column("orders", "idempotency_fingerprint")
    op.drop_constraint("fk_products_category_slug", "products", type_="foreignkey")
    op.drop_table("categories")
