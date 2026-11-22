"""Role permissions.

Roles live on store memberships. Permissions are derived here so a client
cannot grant itself access by sending a role or a store id.
"""

from enum import Enum


class MemberRole(str, Enum):
    OWNER = "OWNER"
    ADMIN = "ADMIN"
    MANAGER = "MANAGER"
    SUPPORT_AGENT = "SUPPORT_AGENT"
    CUSTOMER = "CUSTOMER"


class Permission(str, Enum):
    STORE_READ = "store:read"
    STORE_UPDATE = "store:update"
    MEMBERSHIP_READ = "membership:read"
    MEMBERSHIP_MANAGE = "membership:manage"
    AUDIT_READ = "audit:read"
    ORDER_READ = "order:read"
    ORDER_READ_OWN = "order:read_own"
    RETURN_READ = "return:read"
    RETURN_READ_OWN = "return:read_own"
    RETURN_CREATE = "return:create"
    RETURN_MANAGE = "return:manage"
    KNOWLEDGE_READ = "knowledge:read"
    KNOWLEDGE_MANAGE = "knowledge:manage"


ROLE_PERMISSIONS: dict[MemberRole, frozenset[Permission]] = {
    MemberRole.OWNER: frozenset(Permission),
    MemberRole.ADMIN: frozenset(
        {
            Permission.STORE_READ,
            Permission.STORE_UPDATE,
            Permission.MEMBERSHIP_READ,
            Permission.MEMBERSHIP_MANAGE,
            Permission.AUDIT_READ,
            Permission.ORDER_READ,
            Permission.RETURN_READ,
            Permission.RETURN_MANAGE,
            Permission.KNOWLEDGE_READ,
            Permission.KNOWLEDGE_MANAGE,
        }
    ),
    MemberRole.MANAGER: frozenset(
        {
            Permission.STORE_READ,
            Permission.MEMBERSHIP_READ,
            Permission.AUDIT_READ,
            Permission.ORDER_READ,
            Permission.RETURN_READ,
            Permission.RETURN_MANAGE,
            Permission.KNOWLEDGE_READ,
            Permission.KNOWLEDGE_MANAGE,
        }
    ),
    MemberRole.SUPPORT_AGENT: frozenset(
        {
            Permission.STORE_READ,
            Permission.MEMBERSHIP_READ,
            Permission.ORDER_READ,
            Permission.RETURN_READ,
            Permission.RETURN_MANAGE,
            Permission.KNOWLEDGE_READ,
        }
    ),
    MemberRole.CUSTOMER: frozenset(
        {
            Permission.STORE_READ,
            Permission.ORDER_READ_OWN,
            Permission.RETURN_READ_OWN,
            Permission.RETURN_CREATE,
        }
    ),
}


def permissions_for(role: MemberRole) -> frozenset[Permission]:
    return ROLE_PERMISSIONS[role]


def has_permission(role: MemberRole, permission: Permission) -> bool:
    return permission in permissions_for(role)
