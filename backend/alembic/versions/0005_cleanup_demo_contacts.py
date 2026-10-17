from alembic import op
import sqlalchemy as sa


revision = "0005_cleanup_demo_contacts"
down_revision = "0004_icon_assets"
branch_labels = None
depends_on = None


def upgrade() -> None:
    connection = op.get_bind()
    connection.execute(
        sa.text(
            "UPDATE store_settings SET phone = '', email = '', working_hours = '' "
            "WHERE id = 1 AND phone = :phone AND email = :email"
        ),
        {"phone": "+1 555 010 2026", "email": "hello@example.com"},
    )


def downgrade() -> None:
    pass
