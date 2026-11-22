"""Version 1 API router."""

from fastapi import APIRouter

from app.api.v1.endpoints.ai_review import router as ai_review_router
from app.api.v1.endpoints.analytics import router as analytics_router
from app.api.v1.endpoints.auth import router as auth_router
from app.api.v1.endpoints.dev import router as dev_router
from app.api.v1.endpoints.eligibility import router as eligibility_router
from app.api.v1.endpoints.fulfillment import router as fulfillment_router
from app.api.v1.endpoints.health import router as health_router
from app.api.v1.endpoints.knowledge import router as knowledge_router
from app.api.v1.endpoints.orders import router as orders_router
from app.api.v1.endpoints.profile import router as profile_router
from app.api.v1.endpoints.rag import router as rag_router
from app.api.v1.endpoints.returns import router as returns_router
from app.api.v1.endpoints.stores import router as stores_router

api_router = APIRouter()
api_router.include_router(health_router, tags=["health"])
api_router.include_router(auth_router, tags=["auth"])
api_router.include_router(profile_router, tags=["profile"])
api_router.include_router(stores_router, tags=["stores"])
api_router.include_router(analytics_router, tags=["analytics"])
api_router.include_router(orders_router, tags=["orders"])
api_router.include_router(returns_router, tags=["returns"])
api_router.include_router(fulfillment_router, tags=["fulfillment"])
api_router.include_router(ai_review_router, tags=["ai-review"])
api_router.include_router(eligibility_router, tags=["eligibility"])
api_router.include_router(knowledge_router, tags=["knowledge"])
api_router.include_router(rag_router, tags=["knowledge-rag"])
api_router.include_router(dev_router, tags=["development"])
