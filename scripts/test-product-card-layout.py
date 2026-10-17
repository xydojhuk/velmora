#!/usr/bin/env python3
"""Standalone CSS regression smoke test. Requires: pip install playwright; Chromium."""
from pathlib import Path
import os
import base64
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
css = '\n'.join((ROOT / path).read_text() for path in [
    'frontend/src/styles/var.css',
    'frontend/src/styles/main.css',
    'frontend/src/styles/shared.css',
    'frontend/src/styles/components/product.css',
])
screenshots = Path(os.environ.get('VELMORA_SCREENSHOT_DIR', '/tmp/velmora-card-screenshots'))
screenshots.mkdir(parents=True, exist_ok=True)
img_path = 'data:image/png;base64,' + base64.b64encode((ROOT / 'frontend/public/img/product-handle.png').read_bytes()).decode()
markup = f'''<!doctype html><html><head><meta charset="UTF-8"><style>{css}</style></head>
<body><main class="page"><section class="products">
<article class="product ui-card">
<div class="product__image-wrapper"><img class="product__image" src="{img_path}" alt="Product"></div>
<div class="product__content">
<h2 class="product__title ui-display">Velmora Sentinel H1</h2>
<p class="product__subtitle">Extended-runtime field detector with a dual-display interface</p>
<p class="product__description">A rugged portable analog FPV detector built around parallel tri-band monitoring, a dedicated signal display, and a larger video confirmation screen.</p>
<div class="product__content-bottom"><ul class="product__characteristics">
<li class="product__characteristic"><span class="product__characteristic-icon">◉</span><span class="product__characteristic-label">Battery</span><strong class="product__characteristic-value">12,000 mAh</strong></li>
<li class="product__characteristic"><span class="product__characteristic-icon">◉</span><span class="product__characteristic-label">Runtime</span><strong class="product__characteristic-value">6–8 h</strong></li>
<li class="product__characteristic"><span class="product__characteristic-icon">◉</span><span class="product__characteristic-label">Display</span><strong class="product__characteristic-value">Dual-screen</strong></li>
<li class="product__characteristic"><span class="product__characteristic-icon">◉</span><span class="product__characteristic-label">Dimensions</span><strong class="product__characteristic-value">220 × 135 × 42 mm</strong></li>
</ul><div class="product__purchase"><div class="product__purchase-card ui-card"><div class="product__price ui-display">$429.00</div><div class="product__stock">🟢 Available to order</div><a class="product__order-button btn btn-primary">Order</a><a class="product__details-button">View details →</a></div></div></div>
</div></article></section></main></body></html>'''

with sync_playwright() as p:
    browser = p.chromium.launch(executable_path=os.environ.get('CHROME', '/usr/bin/chromium'), headless=True, args=['--no-sandbox'])
    try:
        for w, h in [(360,800),(390,844),(560,900),(768,1024),(900,900),(1024,768),(1200,900),(1366,768),(1440,900),(1920,1080)]:
            page=browser.new_page(viewport={'width':w,'height':h})
            page.goto('about:blank')
            page.set_content(markup)
            height=page.locator('.product').evaluate('(element) => element.getBoundingClientRect().height')
            details=page.locator('.product__details-button').evaluate('(element) => {let a=element.getBoundingClientRect(); let p=element.closest(".product").getBoundingClientRect();return {bottom: a.bottom, outerBottom:p.bottom}}')
            horizontal=page.evaluate('document.documentElement.scrollWidth > window.innerWidth')
            print(f'{w}x{h}: card={height:.0f}px, horizontal_overflow={horizontal}, details_clipped={details["bottom"] > details["outerBottom"] + 1}')
            assert not horizontal, f'horizontal overflow at {w}'
            assert details['bottom'] <= details['outerBottom'] + 1, f'button clipped at {w}'
            if w>=1366: assert height <= 430, 'desktop card too tall'
            if w in (360, 768, 1366, 1440):
                page.screenshot(path=str(screenshots / f'card-{w}.png'), full_page=True)
            page.close()
    finally:
        browser.close()
