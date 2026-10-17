"""storefront builder configuration

Revision ID: 0008_storefront_builder
Revises: 0007_store_profile_and_hours
Create Date: 2026-10-08
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0008_storefront_builder"
down_revision = "0007_store_profile_and_hours"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "store_settings",
        sa.Column(
            "storefront",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )
    op.execute("""
        UPDATE store_settings
        SET storefront = jsonb_build_object(
            'modals', jsonb_build_object(
                'contacts', jsonb_build_object(
                    'title', COALESCE(support_title, 'Order and product support'),
                    'lead', COALESCE(support_description, 'Contact the store for product and order questions.')
                )
            )
        )
    """)
    op.drop_column("store_settings", "support_description")
    op.drop_column("store_settings", "support_title")
    op.alter_column("store_settings", "storefront", server_default=None)


def downgrade() -> None:
    op.add_column("store_settings", sa.Column("support_title", sa.String(length=180), nullable=False, server_default="Order and product support"))
    op.add_column("store_settings", sa.Column("support_description", sa.Text(), nullable=False, server_default="Contact the store for help choosing a configuration, placing an order, setup questions, or warranty support."))
    op.drop_column("store_settings", "storefront")
