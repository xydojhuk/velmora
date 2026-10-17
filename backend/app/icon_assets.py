import re
import uuid
from dataclasses import dataclass
from xml.etree import ElementTree as ET

from defusedxml.ElementTree import fromstring
from fastapi import HTTPException, UploadFile, status

from app.config import settings


_ALLOWED_TAGS = {"svg", "g", "path", "circle", "rect", "line", "polyline", "polygon", "ellipse"}
_ALLOWED_ATTRS = {
    "viewBox", "preserveAspectRatio", "fill", "stroke", "stroke-width", "stroke-linecap", "stroke-linejoin",
    "stroke-miterlimit", "stroke-dasharray", "stroke-dashoffset", "fill-rule", "clip-rule", "opacity",
    "fill-opacity", "stroke-opacity", "d", "points", "x", "y", "x1", "y1", "x2", "y2", "cx", "cy",
    "r", "rx", "ry", "transform"
}
_NUMBER = re.compile(r"^-?(?:\d+(?:\.\d+)?|\.\d+)(?:[eE][+-]?\d+)?%?$")
_PLAIN_NUMBER = re.compile(r"^-?(?:\d+(?:\.\d+)?|\.\d+)(?:[eE][+-]?\d+)?$")
_NUMBER_LIST = re.compile(r"^[0-9eE+.,\-\s]+$")
_PATH_DATA = re.compile(r"^[MmZzLlHhVvCcSsQqTtAa0-9eE+.,\-\s]+$")
_TRANSFORM = re.compile(r"^[A-Za-z0-9eE+.,()\-\s]+$")
_VIEWBOX = re.compile(r"^\s*-?(?:\d+(?:\.\d+)?|\.\d+)(?:[eE][+-]?\d+)?(?:\s+|-?\s*,\s*)-?(?:\d+(?:\.\d+)?|\.\d+)(?:[eE][+-]?\d+)?(?:\s+|\s*,\s*)-?(?:\d+(?:\.\d+)?|\.\d+)(?:[eE][+-]?\d+)?(?:\s+|\s*,\s*)-?(?:\d+(?:\.\d+)?|\.\d+)(?:[eE][+-]?\d+)?\s*$")


@dataclass(frozen=True)
class SanitizedIcon:
    key: str
    label: str
    svg_markup: str
    original_name: str
    size_bytes: int


def _local_name(value: str) -> str:
    return value.rsplit("}", 1)[-1]


def _clean_color(value: str) -> str:
    return "none" if value.strip().lower() == "none" else "currentColor"


def _clean_attr(name: str, value: str) -> str | None:
    value = value.strip()
    if not value or any(token in value.lower() for token in ("javascript:", "data:", "url(")):
        return None
    if name in {"fill", "stroke"}:
        return _clean_color(value)
    if name in {"stroke-linecap"}:
        return value if value in {"butt", "round", "square"} else None
    if name in {"stroke-linejoin"}:
        return value if value in {"miter", "round", "bevel"} else None
    if name in {"fill-rule", "clip-rule"}:
        return value if value in {"nonzero", "evenodd"} else None
    if name == "preserveAspectRatio":
        return value if re.fullmatch(r"(?:none|x(?:Min|Mid|Max)Y(?:Min|Mid|Max)(?:\s+(?:meet|slice))?)", value) else None
    if name == "viewBox":
        return value if _VIEWBOX.fullmatch(value) else None
    if name == "d":
        return value if len(value) <= 24000 and _PATH_DATA.fullmatch(value) else None
    if name == "points":
        return value if len(value) <= 12000 and _NUMBER_LIST.fullmatch(value) else None
    if name == "transform":
        return value if len(value) <= 1000 and _TRANSFORM.fullmatch(value) else None
    if name == "stroke-dasharray":
        return value if len(value) <= 500 and _NUMBER_LIST.fullmatch(value) else None
    if name in {
        "stroke-width", "stroke-miterlimit", "stroke-dashoffset", "opacity", "fill-opacity", "stroke-opacity",
        "x", "y", "x1", "y1", "x2", "y2", "cx", "cy", "r", "rx", "ry"
    }:
        return value if _NUMBER.fullmatch(value) else None
    return None


def _sanitize_element(source: ET.Element, counter: list[int]) -> ET.Element:
    tag = _local_name(source.tag)
    if tag not in _ALLOWED_TAGS:
        raise HTTPException(status_code=422, detail="SVG contains unsupported elements")
    counter[0] += 1
    if counter[0] > settings.icon_svg_max_elements:
        raise HTTPException(status_code=413, detail="SVG contains too many elements")
    target = ET.Element(tag)
    for raw_name, raw_value in source.attrib.items():
        name = _local_name(raw_name)
        if name not in _ALLOWED_ATTRS:
            continue
        value = _clean_attr(name, str(raw_value))
        if value is not None:
            target.set(name, value)
    for child in list(source):
        target.append(_sanitize_element(child, counter))
    return target


def sanitize_svg(raw: bytes) -> str:
    if len(raw) < 20:
        raise HTTPException(status_code=422, detail="The SVG file is empty or corrupted")
    lowered = raw[:4096].lower()
    if b"<!doctype" in lowered or b"<!entity" in lowered:
        raise HTTPException(status_code=422, detail="DOCTYPE and ENTITY are not allowed in SVG files")
    try:
        root = fromstring(raw)
    except Exception:
        raise HTTPException(status_code=422, detail="Invalid SVG file") from None
    if _local_name(root.tag) != "svg":
        raise HTTPException(status_code=422, detail="The root element must be SVG")
    sanitized = _sanitize_element(root, [0])
    view_box = sanitized.attrib.get("viewBox")
    if not view_box:
        width = str(root.attrib.get("width", "")).strip().removesuffix("px")
        height = str(root.attrib.get("height", "")).strip().removesuffix("px")
        if not _PLAIN_NUMBER.fullmatch(width) or not _PLAIN_NUMBER.fullmatch(height):
            raise HTTPException(status_code=422, detail="SVG must contain a valid viewBox")
        sanitized.set("viewBox", f"0 0 {width} {height}")
    sanitized.attrib.pop("width", None)
    sanitized.attrib.pop("height", None)
    sanitized.set("xmlns", "http://www.w3.org/2000/svg")
    sanitized.set("aria-hidden", "true")
    sanitized.set("focusable", "false")
    markup = ET.tostring(sanitized, encoding="unicode", short_empty_elements=True)
    if len(markup.encode("utf-8")) > settings.icon_svg_max_bytes:
        raise HTTPException(status_code=413, detail="The sanitized SVG exceeds the allowed size")
    return markup


async def read_icon_upload(upload: UploadFile, label: str) -> SanitizedIcon:
    if upload.content_type not in {"image/svg+xml", "text/xml", "application/xml", "application/octet-stream"}:
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="Only SVG files are allowed")
    chunks: list[bytes] = []
    received = 0
    while True:
        chunk = await upload.read(65536)
        if not chunk:
            break
        received += len(chunk)
        if received > settings.icon_svg_max_bytes:
            raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="The icon file is too large")
        chunks.append(chunk)
    await upload.close()
    raw = b"".join(chunks)
    markup = sanitize_svg(raw)
    original_name = str(upload.filename or "icon.svg").replace("\x00", "").rsplit("/", 1)[-1].rsplit("\\", 1)[-1][:255]
    return SanitizedIcon(
        key=f"custom-{uuid.uuid4().hex[:16]}",
        label=label.strip(),
        svg_markup=markup,
        original_name=original_name,
        size_bytes=len(markup.encode("utf-8")),
    )
