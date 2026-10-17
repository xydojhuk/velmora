from app.store_defaults import default_storefront
from app.services.store import normalize_storefront


def test_new_storefront_is_generic_and_never_branded_as_demo():
    source = default_storefront()
    assert 'sentinel' not in str(source).lower()
    assert 'fpv' not in str(source).lower()
    assert source['hero']['title']
    assert source['catalog']['title']


def test_storefront_defaults_are_isolated_from_mutations():
    first = default_storefront()
    first['header']['nav'][0]['label'] = 'Changed'
    assert default_storefront()['header']['nav'][0]['label'] != 'Changed'


def test_merging_does_not_lose_existing_admin_customizations():
    existing = {'hero': {'title': 'Coffee and pastries'}, 'header': {'show_hours': True}}
    result = normalize_storefront(existing)
    assert result['hero']['title'] == 'Coffee and pastries'
    assert result['header']['show_hours'] is True
    assert result['theme']['background']
