import io
import uuid
import warnings
from dataclasses import dataclass
from pathlib import Path

from fastapi import HTTPException, UploadFile, status
from PIL import Image, ImageOps, UnidentifiedImageError

from app.config import settings


@dataclass(frozen=True)
class StoredImage:
    storage_name: str
    url: str
    original_name: str
    mime_type: str
    size_bytes: int
    width: int
    height: int


def media_root() -> Path:
    root = Path(settings.media_root).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


def _media_subdir(name: str) -> Path:
    directory = media_root() / name
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def product_media_root() -> Path:
    return _media_subdir("products")


def storefront_media_root() -> Path:
    return _media_subdir("storefront")


async def _store_image(upload: UploadFile, *, subdir: str, min_dimension: int) -> StoredImage:
    allowed_content_types = {"image/jpeg", "image/png", "image/webp"}
    if upload.content_type not in allowed_content_types:
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="Only JPEG, PNG and WebP images are allowed")

    chunks: list[bytes] = []
    received = 0
    while True:
        chunk = await upload.read(1024 * 1024)
        if not chunk:
            break
        received += len(chunk)
        if received > settings.product_image_max_bytes:
            raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="The image file is too large")
        chunks.append(chunk)
    await upload.close()

    if received < 32:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="The image file is empty or invalid")

    raw = b"".join(chunks)
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(raw)) as probe:
                if probe.format not in {"JPEG", "PNG", "WEBP"}:
                    raise HTTPException(status_code=415, detail="Unsupported image format")
                if getattr(probe, "n_frames", 1) != 1:
                    raise HTTPException(status_code=422, detail="Animated images are not allowed")
                width, height = probe.size
                if width < min_dimension or height < min_dimension:
                    raise HTTPException(status_code=422, detail=f"The image resolution must be at least {min_dimension} × {min_dimension}")
                if width * height > settings.product_image_max_pixels:
                    raise HTTPException(status_code=413, detail="The image resolution is too large")
                probe.verify()

        with Image.open(io.BytesIO(raw)) as image:
            image = ImageOps.exif_transpose(image)
            if image.mode not in {"RGB", "RGBA"}:
                image = image.convert("RGBA" if "transparency" in image.info else "RGB")
            width, height = image.size
            output = io.BytesIO()
            image.save(output, format="WEBP", quality=settings.product_image_webp_quality, method=6)
            encoded = output.getvalue()
    except HTTPException:
        raise
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError, Image.DecompressionBombWarning):
        raise HTTPException(status_code=422, detail="The image file is corrupted or invalid") from None

    storage_name = f"{uuid.uuid4().hex}.webp"
    destination = _media_subdir(subdir) / storage_name
    destination.write_bytes(encoded)
    original_name = Path(upload.filename or "image").name.replace("\x00", "")[:255]
    prefix = settings.media_url_prefix.rstrip("/")
    return StoredImage(
        storage_name=storage_name,
        url=f"{prefix}/{subdir}/{storage_name}",
        original_name=original_name,
        mime_type="image/webp",
        size_bytes=len(encoded),
        width=width,
        height=height,
    )


async def store_product_image(upload: UploadFile) -> StoredImage:
    return await _store_image(upload, subdir="products", min_dimension=240)


async def store_storefront_image(upload: UploadFile) -> StoredImage:
    return await _store_image(upload, subdir="storefront", min_dimension=64)


def _delete_media_file(subdir: str, storage_name: str | None) -> None:
    if not storage_name:
        return
    safe_name = Path(storage_name).name
    if safe_name != storage_name:
        return
    path = _media_subdir(subdir) / safe_name
    try:
        path.unlink(missing_ok=True)
    except OSError:
        return


def delete_product_image_file(storage_name: str | None) -> None:
    _delete_media_file("products", storage_name)


def delete_storefront_image_file(storage_name: str | None) -> None:
    _delete_media_file("storefront", storage_name)
