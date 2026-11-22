"""Optional development-only sample commerce data.

Rows are labeled with ``is_sample`` so they are not treated as production orders.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.exceptions import AppError
from app.core.order_enums import OrderStatus, PaymentStatus
from app.core.permissions import MemberRole
from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.product import Product
from app.models.user import User
from app.repositories.orders import OrderRepository
from app.repositories.products import ProductRepository
from app.services.audit import record_audit


async def create_sample_commerce(
    session: AsyncSession,
    settings: Settings,
    *,
    store_id: uuid.UUID,
    actor: User,
    role: MemberRole,
    ip_address: str | None,
) -> dict[str, object]:
    if settings.app_env not in {"development", "test"}:
        raise AppError("Sample data is disabled outside development", code="forbidden", status_code=403)
    if role != MemberRole.OWNER:
        raise AppError("Only a store owner can load sample data", code="forbidden", status_code=403)

    products_repo = ProductRepository(session)
    orders_repo = OrderRepository(session)
    rows, _total = await orders_repo.list_in_store(
        store_id,
        customer_user_id=actor.id,
        page=1,
        page_size=20,
        sort="order_date",
        direction="desc",
        status=None,
        payment_status=None,
        q=None,
    )
    if any(order.is_sample for order, *_ in rows):
        raise AppError("Sample orders already exist for your account", code="sample_exists", status_code=409)

    catalog = [
        ("SAMPLE-JACKET-01", "Sample field jacket", Decimal("129.00")),
        ("SAMPLE-TEE-02", "Sample organic tee", Decimal("32.00")),
    ]
    product_ids: list[uuid.UUID] = []
    for sku, name, _price in catalog:
        product = Product(store_id=store_id, sku=sku, name=name)
        products_repo.add(product)
        await session.flush()
        product_ids.append(product.id)

    fulfilled_at = datetime.now(UTC) - timedelta(days=3)
    ordered_at = fulfilled_at - timedelta(days=2)
    order = Order(
        store_id=store_id,
        customer_user_id=actor.id,
        order_number=f"SAMPLE-ORD-{uuid.uuid4().hex[:8].upper()}",
        order_date=ordered_at,
        fulfillment_date=fulfilled_at,
        status=OrderStatus.FULFILLED,
        payment_status=PaymentStatus.PAID,
        currency="USD",
        total_amount=Decimal("161.00"),
        is_sample=True,
        return_window_days=30,
    )
    orders_repo.add(order)
    await session.flush()
    session.add_all(
        [
            OrderItem(
                order_id=order.id,
                product_id=product_ids[0],
                quantity=1,
                unit_price=Decimal("129.00"),
                sku="SAMPLE-JACKET-01",
                line_name="Sample field jacket (dev only)",
                item_metadata={"label": "development_sample", "color": "olive"},
            ),
            OrderItem(
                order_id=order.id,
                product_id=product_ids[1],
                quantity=1,
                unit_price=Decimal("32.00"),
                sku="SAMPLE-TEE-02",
                line_name="Sample organic tee (dev only)",
                item_metadata={"label": "development_sample", "size": "M"},
            ),
        ]
    )
    await record_audit(
        session,
        action="dev.sample_commerce_created",
        actor_user_id=actor.id,
        store_id=store_id,
        target_type="order",
        target_id=str(order.id),
        ip_address=ip_address,
        details={"order_number": order.order_number, "is_sample": True},
    )
    await session.commit()
    return {
        "order_id": str(order.id),
        "order_number": order.order_number,
        "is_sample": True,
        "message": "Development sample order created. It is labeled is_sample=true.",
    }