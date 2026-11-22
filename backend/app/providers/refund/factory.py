from app.core.config import Settings, get_settings
from app.providers.refund.mock import MockRefundProvider


def get_refund_provider(settings: Settings | None = None):
    _ = settings or get_settings()
    return MockRefundProvider()