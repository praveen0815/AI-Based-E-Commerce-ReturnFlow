"""Load and version store policy rule configuration."""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import MemberRole, Permission, has_permission
from app.core.exceptions import AppError
from app.models.store_policy_rules import StoreReturnPolicyRule
from app.repositories.policy_rules import PolicyRulesRepository
from app.schemas.policy_rules import StorePolicyRulesConfig
from app.services.audit import record_audit


async def get_active_policy_rules(session: AsyncSession, store_id: uuid.UUID) -> tuple[StorePolicyRulesConfig, int, uuid.UUID]:
    repo = PolicyRulesRepository(session)
    active = await repo.get_active(store_id)
    if active is None:
        config = StorePolicyRulesConfig()
        row = StoreReturnPolicyRule(
            store_id=store_id,
            version=1,
            is_active=True,
            rules=config.model_dump(mode="json"),
            created_by_user_id=None,
        )
        repo.add(row)
        await session.commit()
        await session.refresh(row)
        return config, row.version, row.id
    config = StorePolicyRulesConfig.model_validate(active.rules)
    return config, active.version, active.id


async def publish_policy_rules(
    session: AsyncSession,
    *,
    store_id: uuid.UUID,
    actor_id: uuid.UUID,
    role: MemberRole,
    config: StorePolicyRulesConfig,
    ip_address: str | None,
) -> tuple[StorePolicyRulesConfig, int]:
    if not has_permission(role, Permission.RETURN_MANAGE):
        raise AppError("You do not have permission for this action", code="forbidden", status_code=403)
    repo = PolicyRulesRepository(session)
    await repo.deactivate_all(store_id)
    version = await repo.max_version(store_id) + 1
    row = StoreReturnPolicyRule(
        store_id=store_id,
        version=version,
        is_active=True,
        rules=config.model_dump(mode="json"),
        created_by_user_id=actor_id,
    )
    repo.add(row)
    await record_audit(
        session,
        action="return_policy.published",
        actor_user_id=actor_id,
        store_id=store_id,
        target_type="policy_rules",
        target_id=str(row.id),
        ip_address=ip_address,
        details={"version": version},
    )
    await session.commit()
    return config, version