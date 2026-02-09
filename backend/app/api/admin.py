from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import User, Workspace, WorkspaceMember, Alert
from app.models.stripe_account import StripeAccount
from app.models.user import UserRole
from app.utils.admin import require_admin

router = APIRouter()


# === Schemas ===

class PlatformStats(BaseModel):
    total_users: int
    total_workspaces: int
    total_stripe_accounts: int
    total_alerts: int


class UserAdminResponse(BaseModel):
    id: str
    email: str
    name: str
    email_verified: bool
    roles: List[str]
    workspace_count: int
    created_at: str

    class Config:
        from_attributes = True


class WorkspaceAdminResponse(BaseModel):
    id: str
    name: str
    slug: str
    plan: str
    owner_email: str
    owner_name: str
    member_count: int
    stripe_account_count: int
    created_at: str

    class Config:
        from_attributes = True


class AddRoleRequest(BaseModel):
    role: str


class UserListResponse(BaseModel):
    users: List[UserAdminResponse]
    total: int
    page: int
    page_size: int


class WorkspaceListResponse(BaseModel):
    workspaces: List[WorkspaceAdminResponse]
    total: int
    page: int
    page_size: int


# === Endpoints ===

@router.get("/stats", response_model=PlatformStats)
async def get_platform_stats(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Get platform-wide statistics."""
    users_count = await db.execute(select(func.count()).select_from(User))
    workspaces_count = await db.execute(select(func.count()).select_from(Workspace))
    stripe_accounts_count = await db.execute(select(func.count()).select_from(StripeAccount))
    alerts_count = await db.execute(select(func.count()).select_from(Alert))

    return PlatformStats(
        total_users=users_count.scalar() or 0,
        total_workspaces=workspaces_count.scalar() or 0,
        total_stripe_accounts=stripe_accounts_count.scalar() or 0,
        total_alerts=alerts_count.scalar() or 0,
    )


@router.get("/users", response_model=UserListResponse)
async def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """List all users with workspace counts."""
    query = select(User)

    if search:
        search_pattern = f"%{search}%"
        query = query.where(
            (User.email.ilike(search_pattern)) | (User.name.ilike(search_pattern))
        )

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Apply pagination
    query = query.order_by(User.created_at.desc()).offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    users = result.scalars().all()

    # Get workspace counts for each user
    user_responses = []
    for user in users:
        ws_count_result = await db.execute(
            select(func.count()).where(WorkspaceMember.user_id == user.id)
        )
        workspace_count = ws_count_result.scalar() or 0

        user_responses.append(UserAdminResponse(
            id=str(user.id),
            email=user.email,
            name=user.name,
            email_verified=user.email_verified,
            roles=user.roles or ["user"],
            workspace_count=workspace_count,
            created_at=user.created_at.isoformat(),
        ))

    return UserListResponse(
        users=user_responses,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/workspaces", response_model=WorkspaceListResponse)
async def list_workspaces(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """List all workspaces with owner info."""
    query = select(Workspace).join(User, Workspace.owner_id == User.id)

    if search:
        search_pattern = f"%{search}%"
        query = query.where(
            (Workspace.name.ilike(search_pattern)) | (Workspace.slug.ilike(search_pattern))
        )

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Apply pagination
    query = query.order_by(Workspace.created_at.desc()).offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    workspaces = result.scalars().all()

    # Build response with additional info
    workspace_responses = []
    for workspace in workspaces:
        # Get owner info
        owner_result = await db.execute(select(User).where(User.id == workspace.owner_id))
        owner = owner_result.scalar_one()

        # Get member count
        member_count_result = await db.execute(
            select(func.count()).where(WorkspaceMember.workspace_id == workspace.id)
        )
        member_count = member_count_result.scalar() or 0

        # Get stripe account count
        stripe_count_result = await db.execute(
            select(func.count()).where(StripeAccount.workspace_id == workspace.id)
        )
        stripe_account_count = stripe_count_result.scalar() or 0

        workspace_responses.append(WorkspaceAdminResponse(
            id=str(workspace.id),
            name=workspace.name,
            slug=workspace.slug,
            plan=workspace.plan.value,
            owner_email=owner.email,
            owner_name=owner.name,
            member_count=member_count,
            stripe_account_count=stripe_account_count,
            created_at=workspace.created_at.isoformat(),
        ))

    return WorkspaceListResponse(
        workspaces=workspace_responses,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("/users/{user_id}/roles")
async def add_user_role(
    user_id: str,
    data: AddRoleRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Add a role to a user."""
    # Validate role
    valid_roles = [r.value for r in UserRole]
    if data.role not in valid_roles:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role. Valid roles: {', '.join(valid_roles)}",
        )

    try:
        uuid = UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user ID format")

    result = await db.execute(select(User).where(User.id == uuid))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.add_role(data.role)
    await db.flush()
    await db.refresh(user)

    return {
        "success": True,
        "message": f"Role '{data.role}' added to user",
        "roles": user.roles,
    }


@router.delete("/users/{user_id}/roles/{role}")
async def remove_user_role(
    user_id: str,
    role: str,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Remove a role from a user."""
    try:
        uuid = UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user ID format")

    result = await db.execute(select(User).where(User.id == uuid))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Prevent removing the last 'user' role
    if role == "user" and user.roles == ["user"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot remove the base 'user' role",
        )

    # Prevent admins from removing their own admin role
    if role == "admin" and user.id == admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot remove your own admin role",
        )

    user.remove_role(role)
    await db.flush()
    await db.refresh(user)

    return {
        "success": True,
        "message": f"Role '{role}' removed from user",
        "roles": user.roles,
    }


@router.get("/users/{user_id}")
async def get_user_details(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Get detailed user information."""
    try:
        uuid = UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user ID format")

    result = await db.execute(select(User).where(User.id == uuid))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Get workspaces
    ws_result = await db.execute(
        select(Workspace)
        .join(WorkspaceMember, WorkspaceMember.workspace_id == Workspace.id)
        .where(WorkspaceMember.user_id == user.id)
    )
    workspaces = ws_result.scalars().all()

    return {
        "id": str(user.id),
        "email": user.email,
        "name": user.name,
        "avatar_url": user.avatar_url,
        "email_verified": user.email_verified,
        "roles": user.roles or ["user"],
        "google_id": user.google_id is not None,
        "created_at": user.created_at.isoformat(),
        "updated_at": user.updated_at.isoformat(),
        "workspaces": [
            {
                "id": str(ws.id),
                "name": ws.name,
                "slug": ws.slug,
                "plan": ws.plan.value,
            }
            for ws in workspaces
        ],
    }
