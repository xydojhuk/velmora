import uuid

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0003_store_operations"
down_revision = "0002_product_images"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "store_settings",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("store_name", sa.String(160), nullable=False, server_default="Velmora"),
        sa.Column("phone", sa.String(40), nullable=False, server_default=""),
        sa.Column("email", sa.String(320), nullable=False, server_default=""),
        sa.Column("working_hours", sa.String(160), nullable=False, server_default=""),
        sa.Column("seo_title", sa.String(240), nullable=False, server_default=""),
        sa.Column("seo_description", sa.String(500), nullable=False, server_default=""),
        sa.Column("seo_og_image", sa.String(500), nullable=False, server_default=""),
        sa.Column("maintenance_mode", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("maintenance_title", sa.String(240), nullable=False, server_default="Scheduled maintenance"),
        sa.Column("maintenance_message", sa.Text(), nullable=False, server_default=""),
        sa.Column("orders_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("notification_email_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("notification_email_to", sa.String(320), nullable=False, server_default=""),
        sa.Column("notification_telegram_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("notification_telegram_chat_id", sa.String(120), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_table(
        "shipping_methods",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("code", sa.String(80), nullable=False),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("description", sa.String(500), nullable=False, server_default=""),
        sa.Column("carrier", sa.String(120), nullable=False, server_default=""),
        sa.Column("requires_city", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("requires_branch", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("requires_address", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("price_minor", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("code", name="uq_shipping_methods_code"),
        sa.CheckConstraint("price_minor >= 0", name="ck_shipping_methods_price_nonnegative"),
    )
    op.create_index("ix_shipping_methods_code", "shipping_methods", ["code"])
    op.create_index("ix_shipping_methods_is_active", "shipping_methods", ["is_active"])
    op.create_index("ix_shipping_methods_sort_order", "shipping_methods", ["sort_order"])
    op.create_table(
        "payment_methods",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("code", sa.String(80), nullable=False),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("description", sa.String(500), nullable=False, server_default=""),
        sa.Column("instructions", sa.Text(), nullable=False, server_default=""),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("code", name="uq_payment_methods_code"),
    )
    op.create_index("ix_payment_methods_code", "payment_methods", ["code"])
    op.create_index("ix_payment_methods_is_active", "payment_methods", ["is_active"])
    op.create_index("ix_payment_methods_sort_order", "payment_methods", ["sort_order"])

    connection = op.get_bind()
    connection.execute(
        sa.text(
            "INSERT INTO store_settings (id, store_name, phone, email, working_hours, seo_title, seo_description, maintenance_title, maintenance_message) "
            "VALUES (1, :store_name, :phone, :email, :hours, :seo_title, :seo_description, :maintenance_title, :maintenance_message)"
        ),
        {
            "store_name": "Velmora",
            "phone": "+1 555 010 2026",
            "email": "hello@example.com",
            "hours": "Mon–Sun 09:00–20:00",
            "seo_title": "Velmora — self-hosted storefront demo",
            "seo_description": "A configurable Velmora storefront demo featuring the TM-FPV-DET-02 product line.",
            "maintenance_title": "Scheduled maintenance",
            "maintenance_message": "We are updating the store. Please try again shortly or contact us directly.",
        },
    )
    shipping = [
        ("pickup-branch", "Carrier branch", "Delivery to a selected carrier branch.", "Carrier", True, True, False, 0, 10),
        ("courier", "Courier delivery", "Courier delivery to the specified address.", "Courier", True, False, True, 0, 20),
        ("manager", "Arrange with store", "The store will confirm a suitable shipping method after checkout.", "", False, False, False, 0, 90),
    ]
    for code, name, description, carrier, city, branch, address, price, sort_order in shipping:
        connection.execute(
            sa.text(
                "INSERT INTO shipping_methods (id, code, name, description, carrier, requires_city, requires_branch, requires_address, price_minor, is_active, sort_order) "
                "VALUES (:id, :code, :name, :description, :carrier, :city, :branch, :address, :price, true, :sort_order)"
            ),
            {"id": uuid.uuid4(), "code": code, "name": name, "description": description, "carrier": carrier, "city": city, "branch": branch, "address": address, "price": price, "sort_order": sort_order},
        )
    payments = [
        ("manager", "Arrange with store", "The payment method will be confirmed with the order.", "Do not send payment until the order is confirmed.", 10),
        ("bank-transfer", "Bank transfer", "Payment details are sent after order confirmation.", "Only use payment details supplied by the store after the order is reviewed.", 20),
    ]
    for code, name, description, instructions, sort_order in payments:
        connection.execute(
            sa.text(
                "INSERT INTO payment_methods (id, code, name, description, instructions, is_active, sort_order) "
                "VALUES (:id, :code, :name, :description, :instructions, true, :sort_order)"
            ),
            {"id": uuid.uuid4(), "code": code, "name": name, "description": description, "instructions": instructions, "sort_order": sort_order},
        )

    op.drop_constraint("ck_products_stock_nonnegative", "products", type_="check")
    op.drop_column("products", "stock_quantity")
    op.drop_index("ix_products_is_published", table_name="products")
    op.drop_column("products", "is_published")


def downgrade() -> None:
    op.add_column("products", sa.Column("is_published", sa.Boolean(), nullable=False, server_default=sa.true()))
    op.create_index("ix_products_is_published", "products", ["is_published"])
    op.add_column("products", sa.Column("stock_quantity", sa.Integer(), nullable=False, server_default="0"))
    op.create_check_constraint("ck_products_stock_nonnegative", "products", "stock_quantity >= 0")
    op.drop_index("ix_payment_methods_sort_order", table_name="payment_methods")
    op.drop_index("ix_payment_methods_is_active", table_name="payment_methods")
    op.drop_index("ix_payment_methods_code", table_name="payment_methods")
    op.drop_table("payment_methods")
    op.drop_index("ix_shipping_methods_sort_order", table_name="shipping_methods")
    op.drop_index("ix_shipping_methods_is_active", table_name="shipping_methods")
    op.drop_index("ix_shipping_methods_code", table_name="shipping_methods")
    op.drop_table("shipping_methods")
    op.drop_table("store_settings")
