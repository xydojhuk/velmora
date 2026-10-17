import io
import os

import pytest
from fastapi import UploadFile
from PIL import Image

os.environ.setdefault("JWT_SECRET", "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_!@#$%^&*()")
os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///./test_media.db")

from app.config import settings
from app.media import store_product_image


@pytest.mark.asyncio
async def test_image_upload_is_reencoded_to_webp(tmp_path):
    previous_root = settings.media_root
    settings.media_root = str(tmp_path)
    try:
        source = io.BytesIO()
        Image.new("RGB", (320, 320), (40, 50, 40)).save(source, format="PNG")
        upload = UploadFile(filename="detector.png", file=io.BytesIO(source.getvalue()), headers={"content-type": "image/png"})
        stored = await store_product_image(upload)
        assert stored.mime_type == "image/webp"
        assert stored.width == 320
        assert stored.height == 320
        assert stored.storage_name.endswith(".webp")
        assert (tmp_path / "products" / stored.storage_name).exists()
    finally:
        settings.media_root = previous_root


@pytest.mark.asyncio
async def test_storefront_image_accepts_small_logo_and_reencodes(tmp_path):
    from app.media import store_storefront_image

    previous_root = settings.media_root
    settings.media_root = str(tmp_path)
    try:
        source = io.BytesIO()
        Image.new("RGBA", (128, 128), (80, 90, 40, 255)).save(source, format="PNG")
        upload = UploadFile(filename="logo.png", file=io.BytesIO(source.getvalue()), headers={"content-type": "image/png"})
        stored = await store_storefront_image(upload)
        assert stored.mime_type == "image/webp"
        assert stored.width == 128
        assert (tmp_path / "storefront" / stored.storage_name).exists()
    finally:
        settings.media_root = previous_root
