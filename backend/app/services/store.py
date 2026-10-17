from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import PaymentMethod, ShippingMethod, StoreSettings
from app.store_defaults import DAY_LABELS, DAY_ORDER, default_business_hours, default_storefront


def normalize_storefront(value: dict | None) -> dict:
    def merge(base, override):
        if isinstance(base, dict):
            source = override if isinstance(override, dict) else {}
            result = {key: merge(item, source.get(key)) for key, item in base.items()}
            for key, item in source.items():
                if key not in result:
                    result[key] = item
            return result
        if isinstance(base, list):
            return override if isinstance(override, list) else base
        return base if override is None else override

    return merge(default_storefront(), value or {})


def normalize_business_hours(value: list[dict] | None) -> list[dict]:
    incoming = {str(item.get("day", "")): item for item in (value or []) if isinstance(item, dict)}
    result: list[dict] = []
    for default in default_business_hours():
        item = incoming.get(default["day"], default)
        result.append(
            {
                "day": default["day"],
                "enabled": bool(item.get("enabled", default["enabled"])),
                "open": str(item.get("open") or default["open"]),
                "close": str(item.get("close") or default["close"]),
            }
        )
    return result


def _range_label(days: list[str]) -> str:
    if not days:
        return ""
    indexes = [DAY_ORDER.index(day) for day in days]
    contiguous = indexes == list(range(indexes[0], indexes[0] + len(indexes)))
    if contiguous and len(days) >= 3:
        return f"{DAY_LABELS[days[0]]}–{DAY_LABELS[days[-1]]}"
    return ", ".join(DAY_LABELS[day] for day in days)


def format_business_hours(value: list[dict] | None, timezone: str = "UTC") -> str:
    schedule = normalize_business_hours(value)
    groups: list[tuple[tuple[str, str], list[str]]] = []
    current_key: tuple[str, str] | None = None
    current_days: list[str] = []

    for item in schedule:
        if not item["enabled"]:
            if current_key and current_days:
                groups.append((current_key, current_days))
                current_key, current_days = None, []
            continue
        key = (item["open"], item["close"])
        if current_key == key:
            current_days.append(item["day"])
        else:
            if current_key and current_days:
                groups.append((current_key, current_days))
            current_key, current_days = key, [item["day"]]
    if current_key and current_days:
        groups.append((current_key, current_days))

    if not groups:
        return "Closed"
    parts = [f"{_range_label(days)} · {times[0]}–{times[1]}" for times, days in groups]
    timezone = (timezone or "UTC").strip()
    return " · ".join(parts) + (f" · {timezone}" if timezone else "")


def get_or_create_store_settings(db: Session) -> StoreSettings:
    config = db.get(StoreSettings, 1)
    if config:
        if not config.business_hours:
            config.business_hours = default_business_hours()
        if not config.timezone:
            config.timezone = "UTC"
        if not config.working_hours:
            config.working_hours = format_business_hours(config.business_hours, config.timezone)
        normalized_storefront = normalize_storefront(config.storefront)
        if normalized_storefront != config.storefront:
            config.storefront = normalized_storefront
        return config
    config = StoreSettings(
        id=1,
        business_hours=default_business_hours(),
        timezone="UTC",
        storefront=default_storefront(),
    )
    config.working_hours = format_business_hours(config.business_hours, config.timezone)
    db.add(config)
    db.flush()
    return config


def active_shipping_methods(db: Session) -> list[ShippingMethod]:
    return db.scalars(
        select(ShippingMethod).where(ShippingMethod.is_active.is_(True)).order_by(ShippingMethod.sort_order, ShippingMethod.name)
    ).all()


def active_payment_methods(db: Session) -> list[PaymentMethod]:
    return db.scalars(
        select(PaymentMethod).where(PaymentMethod.is_active.is_(True)).order_by(PaymentMethod.sort_order, PaymentMethod.name)
    ).all()
