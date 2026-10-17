from fastapi import APIRouter

from app.api import analytics, audit_logs, auth, categories, customers, icons, orders, products, public, settings, users


api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(public.router)
api_router.include_router(users.router)
api_router.include_router(products.router)
api_router.include_router(categories.router)
api_router.include_router(icons.router)
api_router.include_router(orders.router)
api_router.include_router(customers.router)
api_router.include_router(settings.router)
api_router.include_router(analytics.router)
api_router.include_router(audit_logs.router)
