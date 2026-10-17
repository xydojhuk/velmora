import pytest
from pydantic import ValidationError
from app.schemas.settings import StorefrontConfig
from app.store_defaults import default_storefront
from app.services.store import normalize_storefront


def test_platform_defaults_and_existing_shop_config_merge():
    value = normalize_storefront({'hero': {'title':'Local shop'}})
    assert value['hero']['title'] == 'Local shop'
    assert value['platform']['enabled'] is True
    assert value['platform']['repository_url'] == 'https://github.com/xydojhuk/velmora'
    assert StorefrontConfig.model_validate(value).platform.title


def test_platform_links_reject_unsafe_url():
    for unsafe in ['javascript:alert(1)', '//evil.example', 'data:text/html,hi', 'http://example.com']:
        with pytest.raises(ValidationError):
            StorefrontConfig.model_validate({**default_storefront(), 'platform': {'repository_url': unsafe}})


def test_platform_custom_text_and_https():
    settings = StorefrontConfig.model_validate({**default_storefront(), 'platform': {
        'title': 'Velmora project', 'repository_url': 'https://github.com/example/velmora', 'enabled': False
    }})
    assert settings.platform.title == 'Velmora project'
    assert not settings.platform.enabled
