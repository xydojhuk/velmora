#!/usr/bin/env python3
"""Private browser smoke tests for Velmora. Run AFTER installation and npm/Docker build.

Requires: pip install playwright && python -m playwright install chromium
This script only browses pages and does not create orders or modify the DB.
"""
import argparse
import sys
from pathlib import Path

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    raise SystemExit('Playwright missing: python -m pip install playwright')

parser = argparse.ArgumentParser()
parser.add_argument('--url', default='http://velmora.local')
parser.add_argument('--screenshots', default='')
args = parser.parse_args()
base = args.url.rstrip('/')

with sync_playwright() as pw:
    browser = pw.chromium.launch(headless=True)
    for width, height in [(360, 800), (390, 844), (768, 1024), (1366, 768), (1440, 900)]:
        page = browser.new_page(viewport={'width': width, 'height': height})
        page.goto(base, wait_until='domcontentloaded', timeout=30000)
        page.locator('.footer__opensource').wait_for(timeout=15000)
        page.locator('.footer__opensource').click()
        dialog = page.locator('.site-modal__dialog')
        dialog.wait_for(timeout=10000)
        link = dialog.locator('a[href="https://github.com/xydojhuk/velmora"]')
        assert link.count() >= 1, 'GitHub button missing'
        modal = dialog.bounding_box()
        assert modal, 'modal bounds missing'
        expected_middle = height / 2
        middle = modal['y'] + modal['height'] / 2
        assert abs(middle - expected_middle) < 4, f'modal not centered: {width}px, center {middle}, target {expected_middle}'
        assert modal['height'] <= height and modal['y'] >= 0, 'modal overflows viewport'
        dialog.locator('.site-modal__close').click()
        assert not page.locator('.site-modal.is-open').count(), 'modal did not close'
        if width == 1366:
            order = page.locator('.product__order-button').first
            if order.count():
                order.click()
                page.locator('.checkout-page .checkout-form').wait_for(timeout=20000)
                assert '/checkout/' in page.url, f'incorrect checkout URL {page.url}'
                print('PASS: client-side checkout navigation loads product without a 404')
            else:
                print('SKIP: no orderable products on storefront')
        horizontal_overflow = page.evaluate('document.documentElement.scrollWidth > window.innerWidth + 1')
        assert not horizontal_overflow, f'horizontal page overflow at {width}px'
        if args.screenshots:
            folder = Path(args.screenshots)
            folder.mkdir(exist_ok=True, parents=True)
            page.screenshot(path=str(folder / f'velmora-{width}.png'))
        print(f'PASS: storefront/modal layout {width}x{height}')
        page.close()
    browser.close()
