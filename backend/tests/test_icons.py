import os

os.environ.setdefault("JWT_SECRET", "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_!@#$%^&*()")
os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///./test_icons.db")

import pytest
from fastapi import HTTPException

from app.icon_assets import sanitize_svg


def test_icon_svg_is_sanitized():
    source = b'<svg viewBox="0 0 24 24" width="24" height="24"><path d="M2 2 L22 22" stroke="black" fill="none" onclick="alert(1)"/></svg>'
    result = sanitize_svg(source)
    assert 'onclick' not in result
    assert 'width="24"' not in result
    assert 'height="24"' not in result
    assert 'stroke="currentColor"' in result
    assert 'viewBox="0 0 24 24"' in result


def test_icon_svg_colors_inherit_current_color():
    source = b'<svg viewBox="0 0 24 24"><path d="M1 1 L23 23" fill="#000" stroke="#ff0000"/><path d="M1 23 L23 1" fill="none" stroke="black"/></svg>'
    result = sanitize_svg(source)
    assert 'fill="currentColor"' in result
    assert 'stroke="currentColor"' in result
    assert 'fill="none"' in result


def test_icon_svg_rejects_script():
    source = b'<svg viewBox="0 0 24 24"><script>alert(1)</script></svg>'
    with pytest.raises(HTTPException):
        sanitize_svg(source)


def test_icon_svg_rejects_external_resource():
    source = b'<svg viewBox="0 0 24 24"><image href="https://example.com/x.png" /></svg>'
    with pytest.raises(HTTPException):
        sanitize_svg(source)
