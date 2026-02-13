import re
import secrets
import uuid
from datetime import datetime, timedelta
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models import User, Workspace, WorkspaceMember
from app.models.workspace import WorkspaceRole as DBWorkspaceRole
from app.schemas import (
    WorkspaceCreate,
    WorkspaceUpdate,
    WorkspaceResponse,
    WorkspaceMemberResponse,
    WorkspaceWithMembersResponse,
    InviteMemberRequest,
    UpdateMemberRoleRequest,
    WorkspaceRole,
)
from app.utils.auth import get_current_user
from app.services.email_service import send_invitation_email

router = APIRouter()


def slugify(text: str) -> str:
    """Convert text to URL-friendly slug."""
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[-\s]+', '-', text)
    return text


def workspace_to_response(workspace: Workspace) -> WorkspaceResponse:
    return WorkspaceResponse(
        id=str(workspace.id),
        name=workspace.name,
        slug=workspace.slug,
        owner_id=str(workspace.owner_id),
        plan=workspace.plan.value,
        created_at=workspace.created_at,
        updated_at=workspace.updated_at,
    )


def member_to_response(member: WorkspaceMember, user: User) -> WorkspaceMemberResponse:
    return WorkspaceMemberResponse(
        id=str(member.id),
        user_id=str(member.user_id),
        user_email=user.email,
        user_name=user.name,
        role=member.role.value,
        invited_at=member.invited_at,
        joined_at=member.joined_at,
    )


async def get_workspace_with_access(
    workspace_id: str,
    user: User,
    db: AsyncSession,
    required_roles: List[DBWorkspaceRole] = None,
) -> Workspace:
    """Get workspace and verify user has access."""
    try:
        ws_uuid = uuid.UUID(workspace_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid workspace ID format",
        )

    result = await db.execute(
        select(Workspace)
        .options(selectinload(Workspace.members).selectinload(WorkspaceMember.user))
        .where(Workspace.id == ws_uuid)
    )
    workspace = result.scalar_one_or_none()

    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found",
        )

    # Check if user is a member
    member = next(
        (m for m in workspace.members if m.user_id == user.id),
        None
    )

    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this workspace",
        )

    if required_roles and member.role not in required_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission for this action",
        )

    return workspace


@router.post("", response_model=WorkspaceResponse)
async def create_workspace(
    data: WorkspaceCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new workspace."""
    # Generate slug if not provided
    slug = data.slug if data.slug else slugify(data.name)

    # Check if slug is unique
    result = await db.execute(select(Workspace).where(Workspace.slug == slug))
    if result.scalar_one_or_none():
        # Append random suffix to make unique
        slug = f"{slug}-{uuid.uuid4().hex[:6]}"

    # Create workspace
    workspace = Workspace(
        name=data.name,
        slug=slug,
        owner_id=current_user.id,
    )
    db.add(workspace)
    await db.flush()

    # Add owner as a member with owner role
    member = WorkspaceMember(
        workspace_id=workspace.id,
        user_id=current_user.id,
        role=DBWorkspaceRole.OWNER,
        joined_at=datetime.utcnow(),
    )
    db.add(member)
    await db.flush()
    await db.refresh(workspace)

    return workspace_to_response(workspace)


@router.get("", response_model=List[WorkspaceResponse])
async def list_workspaces(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all workspaces for the current user."""
    result = await db.execute(
        select(Workspace)
        .join(WorkspaceMember)
        .where(WorkspaceMember.user_id == current_user.id)
        .order_by(Workspace.created_at.desc())
    )
    workspaces = result.scalars().all()

    return [workspace_to_response(ws) for ws in workspaces]


@router.get("/{workspace_id}", response_model=WorkspaceWithMembersResponse)
async def get_workspace(
    workspace_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get workspace details with members."""
    workspace = await get_workspace_with_access(workspace_id, current_user, db)

    members = [
        member_to_response(m, m.user)
        for m in workspace.members
    ]

    return WorkspaceWithMembersResponse(
        workspace=workspace_to_response(workspace),
        members=members,
    )


@router.put("/{workspace_id}", response_model=WorkspaceResponse)
async def update_workspace(
    workspace_id: str,
    data: WorkspaceUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update workspace settings. Requires owner or admin role."""
    workspace = await get_workspace_with_access(
        workspace_id,
        current_user,
        db,
        required_roles=[DBWorkspaceRole.OWNER, DBWorkspaceRole.ADMIN],
    )

    if data.name is not None:
        workspace.name = data.name

    workspace.updated_at = datetime.utcnow()
    await db.flush()
    await db.refresh(workspace)

    return workspace_to_response(workspace)


@router.post("/{workspace_id}/members", response_model=WorkspaceMemberResponse)
async def invite_member(
    workspace_id: str,
    data: InviteMemberRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Invite a member to the workspace. Requires owner or admin role."""
    workspace = await get_workspace_with_access(
        workspace_id,
        current_user,
        db,
        required_roles=[DBWorkspaceRole.OWNER, DBWorkspaceRole.ADMIN],
    )

    # Cannot invite as owner
    if data.role == WorkspaceRole.owner:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot invite someone as owner",
        )

    # Find or create user by email
    result = await db.execute(select(User).where(User.email == data.email))
    invite_user = result.scalar_one_or_none()

    if not invite_user:
        # Create a placeholder user account
        invite_user = User(
            email=data.email,
            name=data.email.split("@")[0],
            email_verified=False,
        )
        db.add(invite_user)
        await db.flush()

    # Check if already a member
    existing_member = next(
        (m for m in workspace.members if m.user_id == invite_user.id),
        None
    )

    if existing_member:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is already a member of this workspace",
        )

    # Map schema role to DB role
    db_role = DBWorkspaceRole(data.role.value)

    # Generate secure invitation token (32 bytes = 64 hex characters)
    invitation_token = secrets.token_urlsafe(32)
    token_expires_at = datetime.utcnow() + timedelta(days=7)

    # Create membership with invitation token
    member = WorkspaceMember(
        workspace_id=workspace.id,
        user_id=invite_user.id,
        role=db_role,
        invited_at=datetime.utcnow(),
        invitation_token=invitation_token,
        token_expires_at=token_expires_at,
        # joined_at stays NULL until invitation is accepted
    )
    db.add(member)
    await db.flush()
    await db.refresh(member)

    # Send invitation email
    await send_invitation_email(
        db=db,
        to_email=invite_user.email,
        inviter_name=current_user.name,
        workspace_name=workspace.name,
        invitation_token=invitation_token,
        workspace_id=workspace.id,
        user_name=invite_user.name
    )

    return member_to_response(member, invite_user)


@router.delete("/{workspace_id}/members/{user_id}")
async def remove_member(
    workspace_id: str,
    user_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Remove a member from the workspace. Requires owner or admin role."""
    workspace = await get_workspace_with_access(
        workspace_id,
        current_user,
        db,
        required_roles=[DBWorkspaceRole.OWNER, DBWorkspaceRole.ADMIN],
    )

    try:
        target_user_id = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user ID format",
        )

    # Find the member
    member = next(
        (m for m in workspace.members if m.user_id == target_user_id),
        None
    )

    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found in this workspace",
        )

    # Cannot remove owner
    if member.role == DBWorkspaceRole.OWNER:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot remove the workspace owner",
        )

    # Only owner can remove admins
    current_member = next(m for m in workspace.members if m.user_id == current_user.id)
    if member.role == DBWorkspaceRole.ADMIN and current_member.role != DBWorkspaceRole.OWNER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the owner can remove admins",
        )

    await db.delete(member)
    await db.flush()

    return {"message": "Member removed successfully"}


@router.put("/{workspace_id}/members/{user_id}", response_model=WorkspaceMemberResponse)
async def update_member_role(
    workspace_id: str,
    user_id: str,
    data: UpdateMemberRoleRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a member's role. Requires owner role for admin changes."""
    workspace = await get_workspace_with_access(
        workspace_id,
        current_user,
        db,
        required_roles=[DBWorkspaceRole.OWNER, DBWorkspaceRole.ADMIN],
    )

    try:
        target_user_id = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user ID format",
        )

    # Find the member
    member = next(
        (m for m in workspace.members if m.user_id == target_user_id),
        None
    )

    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found in this workspace",
        )

    # Cannot change owner role
    if member.role == DBWorkspaceRole.OWNER:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot change the owner's role",
        )

    # Cannot promote to owner
    if data.role == WorkspaceRole.owner:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot promote to owner role",
        )

    # Only owner can promote/demote admins
    current_member = next(m for m in workspace.members if m.user_id == current_user.id)
    if (
        (member.role == DBWorkspaceRole.ADMIN or data.role == WorkspaceRole.admin)
        and current_member.role != DBWorkspaceRole.OWNER
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the owner can change admin roles",
        )

    # Map schema role to DB role
    db_role = DBWorkspaceRole(data.role.value)
    member.role = db_role

    await db.flush()
    await db.refresh(member)

    # Get user for response
    result = await db.execute(select(User).where(User.id == target_user_id))
    user = result.scalar_one()

    return member_to_response(member, user)
