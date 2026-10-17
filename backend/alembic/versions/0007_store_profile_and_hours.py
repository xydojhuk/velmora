"""store profile and structured business hours

Revision ID: 0007_store_profile_and_hours
Revises: 0006_store_service_region
Create Date: 2026-10-08
"""

import json

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0007_store_profile_and_hours"
down_revision = "0006_store_service_region"
branch_labels = None
depends_on = None


def upgrade() -> None:
    default_hours = json.dumps([
        {"day": "mon", "enabled": True, "open": "09:00", "close": "18:00"},
        {"day": "tue", "enabled": True, "open": "09:00", "close": "18:00"},
        {"day": "wed", "enabled": True, "open": "09:00", "close": "18:00"},
        {"day": "thu", "enabled": True, "open": "09:00", "close": "18:00"},
        {"day": "fri", "enabled": True, "open": "09:00", "close": "18:00"},
        {"day": "sat", "enabled": True, "open": "09:00", "close": "18:00"},
        {"day": "sun", "enabled": False, "open": "09:00", "close": "18:00"},
    ]).replace("'", "''")
    op.add_column("store_settings", sa.Column("brand_tagline", sa.String(length=120), nullable=False, server_default="FPV DETECTION"))
    op.add_column(
        "store_settings",
        sa.Column(
            "footer_description",
            sa.Text(),
            nullable=False,
            server_default="Velmora Sentinel systems for analog FPV video signal detection, field monitoring, and online ordering.",
        ),
    )
    op.add_column("store_settings", sa.Column("support_title", sa.String(length=180), nullable=False, server_default="Order and product support"))
    op.add_column(
        "store_settings",
        sa.Column(
            "support_description",
            sa.Text(),
            nullable=False,
            server_default="Contact the store for help choosing a configuration, placing an order, setup questions, or warranty support.",
        ),
    )
    op.add_column(
        "store_settings",
        sa.Column(
            "business_hours",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text(f"'{default_hours}'::jsonb"),
        ),
    )
    op.add_column("store_settings", sa.Column("timezone", sa.String(length=64), nullable=False, server_default="UTC"))
    op.alter_column("store_settings", "working_hours", type_=sa.String(length=240), existing_type=sa.String(length=160), existing_nullable=False)
    op.execute("UPDATE store_settings SET working_hours = 'Mon–Sat · 09:00–18:00 · UTC' WHERE working_hours IS NULL OR working_hours = ''")

    for column in ["brand_tagline", "footer_description", "support_title", "support_description", "business_hours", "timezone"]:
        op.alter_column("store_settings", column, server_default=None)


def downgrade() -> None:
    op.alter_column("store_settings", "working_hours", type_=sa.String(length=160), existing_type=sa.String(length=240), existing_nullable=False)
    op.drop_column("store_settings", "timezone")
    op.drop_column("store_settings", "business_hours")
    op.drop_column("store_settings", "support_description")
    op.drop_column("store_settings", "support_title")
    op.drop_column("store_settings", "footer_description")
    op.drop_column("store_settings", "brand_tagline")
