"""add service region to store settings

Revision ID: 0006_store_service_region
Revises: 0005_cleanup_demo_contacts
Create Date: 2026-10-07
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0006_store_service_region"
down_revision = "0005_cleanup_demo_contacts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('store_settings', sa.Column('service_region', sa.String(length=120), nullable=False, server_default='Worldwide'))
    op.execute("UPDATE store_settings SET service_region = 'Worldwide' WHERE service_region IS NULL OR service_region = ''")
    op.alter_column('store_settings', 'service_region', server_default=None)


def downgrade() -> None:
    op.drop_column('store_settings', 'service_region')
