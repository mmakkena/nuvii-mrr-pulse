from typing import List

from fastapi import Depends, HTTPException, status

from app.models import User
from app.utils.auth import get_current_user


async def require_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Dependency that requires the current user to have the admin role.
    Raises 403 Forbidden if user is not an admin.
    """
    if not current_user.has_role("admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user


def require_roles(required_roles: List[str]):
    """
    Factory function that creates a dependency requiring any of the specified roles.

    Usage:
        @router.get("/endpoint")
        async def endpoint(user: User = Depends(require_roles(["admin", "support"]))):
            ...
    """
    async def dependency(
        current_user: User = Depends(get_current_user),
    ) -> User:
        user_roles = current_user.roles or []
        has_required_role = any(role in user_roles for role in required_roles)

        if not has_required_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"One of these roles required: {', '.join(required_roles)}",
            )
        return current_user

    return dependency
