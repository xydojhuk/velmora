import json
import uuid
from pathlib import PurePosixPath

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0002_product_images"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "product_images",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("products.id", ondelete="CASCADE"), nullable=False),
        sa.Column("storage_name", sa.String(160), nullable=True),
        sa.Column("url", sa.String(500), nullable=False),
        sa.Column("original_name", sa.String(255), nullable=False, server_default=""),
        sa.Column("mime_type", sa.String(80), nullable=False, server_default="image/webp"),
        sa.Column("size_bytes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("width", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("height", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("alt_text", sa.String(240), nullable=False, server_default=""),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("size_bytes >= 0", name="ck_product_images_size_nonnegative"),
        sa.CheckConstraint("width >= 0", name="ck_product_images_width_nonnegative"),
        sa.CheckConstraint("height >= 0", name="ck_product_images_height_nonnegative"),
        sa.UniqueConstraint("storage_name", name="uq_product_images_storage_name"),
    )
    op.create_index("ix_product_images_product_id", "product_images", ["product_id"])
    op.create_index("ix_product_images_product_sort", "product_images", ["product_id", "sort_order"])

    connection = op.get_bind()
    rows = connection.execute(sa.text("SELECT id, title, primary_image, gallery FROM products")).mappings().all()
    for row in rows:
        gallery = row["gallery"] or []
        if isinstance(gallery, str):
            try:
                gallery = json.loads(gallery)
            except json.JSONDecodeError:
                gallery = []
        urls = []
        for value in [row["primary_image"], *gallery]:
            if value and value not in urls:
                urls.append(value)
        for index, url in enumerate(urls[:4]):
            original_name = PurePosixPath(str(url).split("?", 1)[0]).name[:255]
            connection.execute(
                sa.text(
                    "INSERT INTO product_images (id, product_id, storage_name, url, original_name, mime_type, size_bytes, width, height, alt_text, sort_order) "
                    "VALUES (:id, :product_id, NULL, :url, :original_name, 'image/legacy', 0, 0, 0, :alt_text, :sort_order)"
                ),
                {
                    "id": uuid.uuid4(),
                    "product_id": row["id"],
                    "url": str(url),
                    "original_name": original_name,
                    "alt_text": str(row["title"])[:240],
                    "sort_order": index,
                },
            )

    op.drop_column("products", "gallery")
    op.drop_column("products", "primary_image")


def downgrade() -> None:
    op.add_column("products", sa.Column("primary_image", sa.String(500), nullable=False, server_default=""))
    op.add_column("products", sa.Column("gallery", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")))
    connection = op.get_bind()
    products = connection.execute(sa.text("SELECT id FROM products")).scalars().all()
    for product_id in products:
        images = connection.execute(
            sa.text("SELECT url FROM product_images WHERE product_id = :product_id ORDER BY sort_order ASC, created_at ASC"),
            {"product_id": product_id},
        ).scalars().all()
        primary = images[0] if images else ""
        connection.execute(
            sa.text("UPDATE products SET primary_image = :primary, gallery = CAST(:gallery AS jsonb) WHERE id = :product_id"),
            {"primary": primary, "gallery": json.dumps(images), "product_id": product_id},
        )
    op.drop_index("ix_product_images_product_sort", table_name="product_images")
    op.drop_index("ix_product_images_product_id", table_name="product_images")
    op.drop_table("product_images")
