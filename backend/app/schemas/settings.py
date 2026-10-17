import re
import uuid
from datetime import datetime
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import EmailStr, Field, field_validator

from app.schemas.common import CleanTextModel, ORMModel, validate_slug
from app.schemas.icons import PublicIconAsset


BusinessDay = Literal["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
NavKey = Literal["home", "catalog", "about", "shipping", "faq", "contacts"]
ActionKind = Literal["catalog", "contacts", "url", "none"]
_HEX_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")


class BusinessHoursEntry(CleanTextModel):
    day: BusinessDay
    enabled: bool = True
    open: str = Field(default="09:00", pattern=r"^(?:[01]\d|2[0-3]):[0-5]\d$")
    close: str = Field(default="18:00", pattern=r"^(?:[01]\d|2[0-3]):[0-5]\d$")


def _validate_timezone(value: str | None) -> str | None:
    if value is None:
        return value
    value = value.strip() or "UTC"
    try:
        ZoneInfo(value)
    except ZoneInfoNotFoundError as exc:
        raise ValueError("Unknown IANA timezone") from exc
    return value


def _validate_schedule(value):
    if value is None:
        return value
    if len(value) != 7:
        raise ValueError("Business hours must contain exactly seven days")
    days = [item.day for item in value]
    if len(set(days)) != 7:
        raise ValueError("Business hours contain duplicate days")
    required = {"mon", "tue", "wed", "thu", "fri", "sat", "sun"}
    if set(days) != required:
        raise ValueError("Business hours must contain Monday through Sunday")
    for item in value:
        if item.enabled and item.open == item.close:
            raise ValueError(f"Opening and closing time cannot be equal for {item.day}")
    return value


def _asset_url(value: str) -> str:
    value = value.strip()
    if not value:
        return ""
    if value.startswith("/") and not value.startswith("//"):
        return value
    if value.startswith("https://"):
        return value
    raise ValueError("Use a local /path or an https:// URL")


def _action_url(value: str) -> str:
    value = value.strip()
    if not value:
        return ""
    if value.startswith("/") and not value.startswith("//"):
        return value
    if value.startswith("https://"):
        return value
    raise ValueError("Links must use a local /path or https:// URL")


class StorefrontBranding(CleanTextModel):
    logo_url: str = Field(default="/img/logo.png", max_length=500)
    logo_alt: str = Field(default="Velmora", max_length=160)

    @field_validator("logo_url")
    @classmethod
    def logo_url_valid(cls, value: str) -> str:
        return _asset_url(value)


class StorefrontTheme(CleanTextModel):
    background: str = "#080A08"
    background_soft: str = "#0D100D"
    surface: str = "#121612"
    surface_alt: str = "#181D17"
    primary: str = "#7F8647"
    accent: str = "#A1A65A"
    accent_soft: str = "#777C43"
    text: str = "#F2F3EE"
    text_secondary: str = "#B7BAAE"
    border: str = "#2C3327"

    @field_validator("*")
    @classmethod
    def color_valid(cls, value: str) -> str:
        if not _HEX_RE.fullmatch(value):
            raise ValueError("Theme colors must use #RRGGBB format")
        return value.upper()


class StorefrontNavItem(CleanTextModel):
    key: NavKey
    label: str = Field(min_length=1, max_length=48)
    enabled: bool = True


class StorefrontAnnouncement(CleanTextModel):
    enabled: bool = False
    text: str = Field(default="", max_length=240)
    link_label: str = Field(default="", max_length=60)
    link_url: str = Field(default="", max_length=500)

    @field_validator("link_url")
    @classmethod
    def link_valid(cls, value: str) -> str:
        return _action_url(value)


class StorefrontHeader(CleanTextModel):
    show_phone: bool = True
    show_hours: bool = False
    show_consultation: bool = True
    consultation_label: str = Field(default="Request consultation", max_length=80)
    nav: list[StorefrontNavItem] = Field(default_factory=list, max_length=12)

    @field_validator("nav")
    @classmethod
    def nav_unique(cls, value: list[StorefrontNavItem]):
        keys = [item.key for item in value]
        if len(keys) != len(set(keys)):
            raise ValueError("Navigation items must be unique")
        return value


class StorefrontAction(CleanTextModel):
    enabled: bool = True
    label: str = Field(default="", max_length=80)
    action: ActionKind = "none"
    url: str = Field(default="", max_length=500)

    @field_validator("url")
    @classmethod
    def url_valid(cls, value: str) -> str:
        return _action_url(value)


class StorefrontFeature(CleanTextModel):
    icon: str = Field(default="pulse", min_length=1, max_length=80)
    title: str = Field(default="", max_length=120)
    text: str = Field(default="", max_length=300)


class StorefrontHero(CleanTextModel):
    enabled: bool = True
    eyebrow: str = Field(default="", max_length=160)
    title: str = Field(default="", max_length=320)
    description: str = Field(default="", max_length=1200)
    image_url: str = Field(default="/img/herobg.png", max_length=500)
    primary_action: StorefrontAction = Field(default_factory=StorefrontAction)
    secondary_action: StorefrontAction = Field(default_factory=StorefrontAction)
    features: list[StorefrontFeature] = Field(default_factory=list, max_length=8)

    @field_validator("image_url")
    @classmethod
    def image_valid(cls, value: str) -> str:
        return _asset_url(value)


class StorefrontCatalog(CleanTextModel):
    show_heading: bool = False
    title: str = Field(default="Catalog", max_length=160)
    description: str = Field(default="", max_length=600)


class StorefrontFeatureStrip(CleanTextModel):
    enabled: bool = True
    items: list[StorefrontFeature] = Field(default_factory=list, max_length=8)


class StorefrontFaqItem(CleanTextModel):
    question: str = Field(min_length=1, max_length=240)
    answer: str = Field(min_length=1, max_length=2000)


class StorefrontFaq(CleanTextModel):
    enabled: bool = True
    title: str = Field(default="Frequently asked questions", max_length=160)
    items: list[StorefrontFaqItem] = Field(default_factory=list, max_length=20)


class StorefrontFooter(CleanTextModel):
    show_menu: bool = True
    show_products: bool = True
    show_contacts: bool = True
    show_callback: bool = True
    callback_title: str = Field(default="Need help choosing?", max_length=140)
    callback_text: str = Field(default="", max_length=600)
    callback_button_label: str = Field(default="Contact us", max_length=80)
    copyright: str = Field(default="© {year} {store}. All rights reserved.", max_length=240)


class StorefrontStat(CleanTextModel):
    value: str = Field(default="", max_length=60)
    label: str = Field(default="", max_length=100)


class StorefrontCard(CleanTextModel):
    eyebrow: str = Field(default="", max_length=80)
    title: str = Field(default="", max_length=160)
    text: str = Field(default="", max_length=1000)


class StorefrontAboutModal(CleanTextModel):
    enabled: bool = True
    eyebrow: str = Field(default="", max_length=160)
    title: str = Field(default="", max_length=220)
    lead: str = Field(default="", max_length=1400)
    stats: list[StorefrontStat] = Field(default_factory=list, max_length=8)
    cards: list[StorefrontCard] = Field(default_factory=list, max_length=8)
    callout_title: str = Field(default="", max_length=180)
    callout_text: str = Field(default="", max_length=1200)


class StorefrontStep(CleanTextModel):
    title: str = Field(default="", max_length=120)
    text: str = Field(default="", max_length=600)


class StorefrontInfoSection(CleanTextModel):
    title: str = Field(default="", max_length=160)
    items: list[str] = Field(default_factory=list, max_length=12)

    @field_validator("items")
    @classmethod
    def items_valid(cls, value: list[str]):
        return [item[:500] for item in value if item]


class StorefrontShippingModal(CleanTextModel):
    enabled: bool = True
    eyebrow: str = Field(default="", max_length=160)
    title: str = Field(default="", max_length=220)
    lead: str = Field(default="", max_length=1400)
    steps: list[StorefrontStep] = Field(default_factory=list, max_length=8)
    sections: list[StorefrontInfoSection] = Field(default_factory=list, max_length=6)
    note: str = Field(default="", max_length=1600)


class StorefrontContactsModal(CleanTextModel):
    title: str = Field(default="", max_length=220)
    lead: str = Field(default="", max_length=1400)
    email_note: str = Field(default="", max_length=180)
    region_note: str = Field(default="", max_length=180)
    cards: list[StorefrontCard] = Field(default_factory=list, max_length=8)
    callout_title: str = Field(default="", max_length=180)
    callout_text: str = Field(default="", max_length=1200)


class StorefrontModals(CleanTextModel):
    about: StorefrontAboutModal = Field(default_factory=StorefrontAboutModal)
    shipping: StorefrontShippingModal = Field(default_factory=StorefrontShippingModal)
    contacts: StorefrontContactsModal = Field(default_factory=StorefrontContactsModal)


class StorefrontPlatform(CleanTextModel):
    enabled: bool = True
    eyebrow: str = Field(default="INDEPENDENT OPEN-SOURCE SOFTWARE", max_length=120)
    title: str = Field(default="Velmora — your store, your server.", max_length=220)
    description: str = Field(default="", max_length=1400)
    support_title: str = Field(default="Support open-source development", max_length=180)
    support_text: str = Field(default="", max_length=1200)
    footer_label: str = Field(default="Powered by Velmora", max_length=80)
    repository_label: str = Field(default="Project on GitHub", max_length=80)
    repository_url: str = Field(default="", max_length=500)
    support_label: str = Field(default="Support the project", max_length=80)
    support_url: str = Field(default="", max_length=500)

    @field_validator("repository_url", "support_url")
    @classmethod
    def platform_link_valid(cls, value: str) -> str:
        return _action_url(value)


class StorefrontConfig(CleanTextModel):
    branding: StorefrontBranding = Field(default_factory=StorefrontBranding)
    theme: StorefrontTheme = Field(default_factory=StorefrontTheme)
    announcement: StorefrontAnnouncement = Field(default_factory=StorefrontAnnouncement)
    header: StorefrontHeader = Field(default_factory=StorefrontHeader)
    hero: StorefrontHero = Field(default_factory=StorefrontHero)
    catalog: StorefrontCatalog = Field(default_factory=StorefrontCatalog)
    feature_strip: StorefrontFeatureStrip = Field(default_factory=StorefrontFeatureStrip)
    faq: StorefrontFaq = Field(default_factory=StorefrontFaq)
    footer: StorefrontFooter = Field(default_factory=StorefrontFooter)
    modals: StorefrontModals = Field(default_factory=StorefrontModals)
    platform: StorefrontPlatform = Field(default_factory=StorefrontPlatform)


class StoreSettingsRead(ORMModel):
    id: int
    store_name: str
    brand_tagline: str
    footer_description: str
    phone: str
    email: str
    working_hours: str
    business_hours: list[BusinessHoursEntry]
    timezone: str
    service_region: str
    storefront: StorefrontConfig
    seo_title: str
    seo_description: str
    seo_og_image: str
    maintenance_mode: bool
    maintenance_title: str
    maintenance_message: str
    orders_enabled: bool
    notification_email_enabled: bool
    notification_email_to: str
    notification_telegram_enabled: bool
    notification_telegram_chat_id: str
    created_at: datetime
    updated_at: datetime


class StoreSettingsUpdate(CleanTextModel):
    store_name: str | None = Field(default=None, min_length=1, max_length=160)
    brand_tagline: str | None = Field(default=None, max_length=120)
    footer_description: str | None = Field(default=None, max_length=800)
    phone: str | None = Field(default=None, max_length=40)
    email: EmailStr | Literal[""] | None = None
    working_hours: str | None = Field(default=None, max_length=240)
    business_hours: list[BusinessHoursEntry] | None = None
    timezone: str | None = Field(default=None, max_length=64)
    service_region: str | None = Field(default=None, max_length=120)
    storefront: StorefrontConfig | None = None
    seo_title: str | None = Field(default=None, max_length=240)
    seo_description: str | None = Field(default=None, max_length=500)
    seo_og_image: str | None = Field(default=None, max_length=500)
    maintenance_mode: bool | None = None
    maintenance_title: str | None = Field(default=None, max_length=240)
    maintenance_message: str | None = Field(default=None, max_length=2000)
    orders_enabled: bool | None = None
    notification_email_enabled: bool | None = None
    notification_email_to: EmailStr | Literal[""] | None = None
    notification_telegram_enabled: bool | None = None
    notification_telegram_chat_id: str | None = Field(default=None, max_length=120)

    @field_validator("timezone")
    @classmethod
    def timezone_valid(cls, value: str | None) -> str | None:
        return _validate_timezone(value)

    @field_validator("business_hours")
    @classmethod
    def business_hours_valid(cls, value):
        return _validate_schedule(value)


class ShippingMethodBase(CleanTextModel):
    code: str = Field(min_length=2, max_length=80)
    name: str = Field(min_length=2, max_length=160)
    description: str = Field(default="", max_length=500)
    carrier: str = Field(default="", max_length=120)
    requires_city: bool = True
    requires_branch: bool = False
    requires_address: bool = False
    price_minor: int = Field(default=0, ge=0, le=2_000_000_000)
    is_active: bool = True
    sort_order: int = Field(default=0, ge=-10000, le=10000)

    @field_validator("code")
    @classmethod
    def code_valid(cls, value: str) -> str:
        return validate_slug(value)


class ShippingMethodCreate(ShippingMethodBase):
    pass


class ShippingMethodUpdate(CleanTextModel):
    code: str | None = Field(default=None, min_length=2, max_length=80)
    name: str | None = Field(default=None, min_length=2, max_length=160)
    description: str | None = Field(default=None, max_length=500)
    carrier: str | None = Field(default=None, max_length=120)
    requires_city: bool | None = None
    requires_branch: bool | None = None
    requires_address: bool | None = None
    price_minor: int | None = Field(default=None, ge=0, le=2_000_000_000)
    is_active: bool | None = None
    sort_order: int | None = Field(default=None, ge=-10000, le=10000)

    @field_validator("code")
    @classmethod
    def code_valid(cls, value: str | None) -> str | None:
        return validate_slug(value) if value else value


class ShippingMethodRead(ORMModel):
    id: uuid.UUID
    code: str
    name: str
    description: str
    carrier: str
    requires_city: bool
    requires_branch: bool
    requires_address: bool
    price_minor: int
    is_active: bool
    sort_order: int
    created_at: datetime
    updated_at: datetime


class PaymentMethodBase(CleanTextModel):
    code: str = Field(min_length=2, max_length=80)
    name: str = Field(min_length=2, max_length=160)
    description: str = Field(default="", max_length=500)
    instructions: str = Field(default="", max_length=2000)
    is_active: bool = True
    sort_order: int = Field(default=0, ge=-10000, le=10000)

    @field_validator("code")
    @classmethod
    def code_valid(cls, value: str) -> str:
        return validate_slug(value)


class PaymentMethodCreate(PaymentMethodBase):
    pass


class PaymentMethodUpdate(CleanTextModel):
    code: str | None = Field(default=None, min_length=2, max_length=80)
    name: str | None = Field(default=None, min_length=2, max_length=160)
    description: str | None = Field(default=None, max_length=500)
    instructions: str | None = Field(default=None, max_length=2000)
    is_active: bool | None = None
    sort_order: int | None = Field(default=None, ge=-10000, le=10000)

    @field_validator("code")
    @classmethod
    def code_valid(cls, value: str | None) -> str | None:
        return validate_slug(value) if value else value


class PaymentMethodRead(ORMModel):
    id: uuid.UUID
    code: str
    name: str
    description: str
    instructions: str
    is_active: bool
    sort_order: int
    created_at: datetime
    updated_at: datetime


class PublicStoreConfig(CleanTextModel):
    store_name: str
    brand_tagline: str
    footer_description: str
    phone: str
    email: str
    working_hours: str
    business_hours: list[BusinessHoursEntry]
    timezone: str
    service_region: str
    storefront: StorefrontConfig
    seo_title: str
    seo_description: str
    seo_og_image: str
    maintenance_mode: bool
    maintenance_title: str
    maintenance_message: str
    orders_enabled: bool
    shipping_methods: list[ShippingMethodRead]
    payment_methods: list[PaymentMethodRead]
    icons: list[PublicIconAsset] = Field(default_factory=list)
