def detail_extra(*, compact: bool = False):
    model_name = "Sentinel C1" if compact else "Sentinel H1"
    return {
        "warranty": "12-month warranty",
        "warranty_note": "Warranty does not cover liquid ingress, mechanical damage, or operation outside the documented limits.",
        "availability_label": "Available to order",
        "unavailable_label": "Orders are temporarily paused",
        "primary_action_label": "Place order",
        "secondary_action_label": "Ask a question",
        "detail_eyebrow": "Velmora {model}",
        "tab_labels": {"description": "Description", "specifications": "Specifications", "usage": "Operation"},
        "specifications_title": "Technical specifications",
        "usage_title": "Before you start",
        "benefits": [
            {"icon": "shield-check", "title": "Warranty", "text": "12-month warranty"},
            {"icon": "connection", "title": "Tri-band scanning", "text": "1.2, 3.3 and 5.8 GHz scanned in parallel"},
            {"icon": "video", "title": "Video confirmation", "text": "Built-in display for received analog video"},
            {"icon": "pulse", "title": "Fast field startup", "text": "Scanning starts immediately after power-on"},
        ],
        "visual_features": [
            {"icon": "connection", "text": "Independent receivers monitor all three frequency bands in parallel"},
            {"icon": "notification", "text": "Visual and audible indication is available when an analog FPV signal is detected"},
            {"icon": "video", "text": "The integrated display can be used to confirm the received analog video feed"},
            {"icon": "radar", "text": "Detection history keeps recently observed frequencies available for review"},
        ],
        "usage_items": [
            "Attach the supplied antennas to the corresponding RF connectors before powering on the device.",
            "Charge through USB Type-C using a 5 V source rated for up to 3 A.",
            "Keep ventilation areas unobstructed and avoid prolonged operation in excessive heat.",
            "Recharge the battery before extended field use and avoid deep discharge during storage.",
            "Do not disconnect power while a firmware update is in progress.",
            "Use the detector as an additional monitoring tool and verify detections using the available video and signal information.",
        ],
        "secondary_sections": [
            {
                "title": "Before ordering", "accent": False,
                "items": [
                    {
                        "icon": "resize",
                        "title": "Choose the right platform",
                        "text": "Sentinel C1 is smaller and optimized for mobile setups." if compact else "Sentinel H1 prioritizes display area and extended field runtime.",
                    },
                    {"icon": "phone", "title": "Confirm your setup", "text": "Ask about antennas, power, mounting, operating bands, and installation before ordering."},
                ],
                "link_label": "Shipping, payment and warranty", "link_modal": "delivery",
            },
            {
                "title": "Important operating limits", "accent": True,
                "checks": [
                    {"icon": "connection", "text": "Designed for analog FPV video signals; digital video systems are outside the target signal set."},
                    {"icon": "radar", "text": "Control and telemetry links are outside the target signal set for the Sentinel detector line."},
                    {"icon": "notification", "text": "Detected signals should be evaluated independently; the device does not identify the operator or origin."},
                    {"icon": "pulse", "text": "Practical range depends on transmitter power, antennas, interference, obstacles, and terrain."},
                ],
            },
        ],
    }


SHARED_SPECS = [
    {"group": "Radio", "label": "1.2 GHz band", "value": "1000–2300 MHz"},
    {"group": "Radio", "label": "3.3 GHz band", "value": "2300–3990 MHz"},
    {"group": "Radio", "label": "5.8 GHz band", "value": "4900–6190 MHz"},
    {"group": "Radio", "label": "Scan mode", "value": "Parallel tri-band monitoring"},
    {"group": "General", "label": "Target signals", "value": "Analog FPV video"},
    {"group": "Interface", "label": "RF connectors", "value": "SMA-Female"},
    {"group": "Power", "label": "Charging", "value": "USB Type-C, 5 V / up to 3 A"},
    {"group": "Software", "label": "Updates", "value": "Wi-Fi firmware update mode"},
]


CURRENT_PRODUCTS = [
    {
        # Keep the legacy demo slug so local-seed upgrades an existing demo database
        # instead of creating a duplicate product.
        "slug": "handle",
        "sku": "VLM-SEN-H1",
        "model": "SEN-H1",
        "name": "Sentinel H1",
        "title": "Velmora Sentinel H1",
        "subtitle": "Extended-runtime field detector with a dual-display interface",
        "short_description": "A rugged portable analog FPV detector built around parallel tri-band monitoring, a dedicated signal display, and a larger video confirmation screen.",
        "description_title": "Sentinel H1 — built for extended field monitoring",
        "description_paragraphs": [
            "Sentinel H1 is the larger field-oriented configuration in the Velmora Sentinel line. Its front panel combines a compact signal-status display with a larger video screen for fast visual confirmation of a received analog feed.",
            "The enclosure is designed around portable operation, physical controls, dual antenna connections, and an extended-capacity battery. The extended-capacity battery targets 6–8 hours of operation under typical monitoring conditions.",
        ],
        "price_minor": 42900,
        "currency": "USD",
        "is_active": True,
        "catalog_metrics": [
            {"icon": "battery", "label": "Battery", "value": "12,000 mAh"},
            {"icon": "clock", "label": "Runtime", "value": "6–8 h"},
            {"icon": "video", "label": "Display", "value": "Dual-screen"},
            {"icon": "resize", "label": "Dimensions", "value": "220 × 135 × 42 mm"},
            {"icon": "weight", "label": "Weight", "value": "780 g"},
            {"icon": "shield-check", "label": "Use", "value": "Portable field"},
        ],
        "summary_features": [
            {"icon": "battery", "text": "12,000 mAh rechargeable battery"},
            {"icon": "clock", "text": "6–8 hours of expected standalone operation"},
            {"icon": "video", "text": "Dedicated signal display plus video confirmation screen"},
            {"icon": "connection", "text": "Dual external antenna connections"},
        ],
        "specifications": SHARED_SPECS + [
            {"group": "Enclosure", "label": "Dimensions", "value": "220 × 135 × 42 mm"},
            {"group": "Enclosure", "label": "Weight", "value": "780 g"},
            {"group": "Enclosure", "label": "Construction", "value": "Rugged polymer shell with reinforced corners"},
            {"group": "Interface", "label": "Displays", "value": "Signal-status display + video confirmation display"},
            {"group": "Power", "label": "Battery", "value": "12,000 mAh rechargeable pack"},
            {"group": "Power", "label": "Expected runtime", "value": "6–8 h"},
        ],
        "extra": detail_extra(compact=False),
        "sort_order": 10,
    },
    {
        # Keep the legacy demo slug for in-place synchronization.
        "slug": "compact",
        "sku": "VLM-SEN-C1",
        "model": "SEN-C1",
        "name": "Sentinel C1",
        "title": "Velmora Sentinel C1",
        "subtitle": "Compact spectrum monitor for mobile and vehicle setups",
        "short_description": "A smaller rugged detector with a spectrum-focused interface, physical controls, and a layout intended for compact mobile installations.",
        "description_title": "Sentinel C1 — compact monitoring without the bulk",
        "description_paragraphs": [
            "Sentinel C1 packages the same tri-band analog FPV monitoring concept into a shorter enclosure intended for vehicle dashboards, compact field kits, and space-limited installations.",
            "Its front panel prioritizes spectrum information and quick physical control. The compact configuration uses active cooling and an 8,000 mAh battery with an expected operating time of 4–5 hours.",
        ],
        "price_minor": 34900,
        "currency": "USD",
        "is_active": True,
        "catalog_metrics": [
            {"icon": "battery", "label": "Battery", "value": "8,000 mAh"},
            {"icon": "clock", "label": "Runtime", "value": "4–5 h"},
            {"icon": "pulse", "label": "Cooling", "value": "Active"},
            {"icon": "resize", "label": "Dimensions", "value": "160 × 145 × 48 mm"},
            {"icon": "weight", "label": "Weight", "value": "620 g"},
            {"icon": "shield-check", "label": "Use", "value": "Mobile / vehicle"},
        ],
        "summary_features": [
            {"icon": "battery", "text": "8,000 mAh rechargeable battery"},
            {"icon": "clock", "text": "4–5 hours of expected standalone operation"},
            {"icon": "pulse", "text": "Active enclosure cooling"},
            {"icon": "radar", "text": "Spectrum-focused monitoring interface"},
        ],
        "specifications": SHARED_SPECS + [
            {"group": "Enclosure", "label": "Dimensions", "value": "160 × 145 × 48 mm"},
            {"group": "Enclosure", "label": "Weight", "value": "620 g"},
            {"group": "Enclosure", "label": "Construction", "value": "Compact rugged polymer shell"},
            {"group": "Enclosure", "label": "Cooling", "value": "Active"},
            {"group": "Interface", "label": "Display", "value": "Spectrum and channel monitoring screen"},
            {"group": "Power", "label": "Battery", "value": "8,000 mAh rechargeable pack"},
            {"group": "Power", "label": "Expected runtime", "value": "4–5 h"},
        ],
        "extra": detail_extra(compact=True),
        "sort_order": 20,
    },
]


CURRENT_PRODUCT_IMAGES = {
    "handle": [
        ("/img/product-handle.png", "Velmora Sentinel H1 — front view", 1448, 1086),
        ("/img/product-handle-detail-display.jpg", "Velmora Sentinel H1 — display and controls", 1200, 900),
        ("/img/product-handle-detail-top.jpg", "Velmora Sentinel H1 — antennas and top controls", 1200, 900),
    ],
    "compact": [
        ("/img/product-compact.png", "Velmora Sentinel C1 — front view", 1448, 1086),
        ("/img/product-compact-detail-display.jpg", "Velmora Sentinel C1 — spectrum display and controls", 1200, 900),
        ("/img/product-compact-detail-top.jpg", "Velmora Sentinel C1 — antennas and top controls", 1200, 900),
    ],
}
