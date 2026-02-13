import logging
import secrets
import uuid
from datetime import datetime
from typing import List
from urllib.parse import urlencode

import stripe
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.database import get_db
from app.models import User, Workspace, WorkspaceMember, StripeAccount
from app.models.audit import AuditLog
from app.models.stripe_account import StripeAccountStatus
from app.models.workspace import WorkspaceRole
from app.schemas import (
    StripeAccountResponse,
    StripeConnectStartResponse,
)
from app.utils.auth import get_current_user
from app.utils.encryption import encrypt_token, decrypt_token

router = APIRouter()

# Initialize Stripe
stripe.api_key = settings.stripe_secret_key

# Logger
logger = logging.getLogger(__name__)


def deauthorize_stripe_oauth(stripe_account_id: str, business_name: str = None):
    """
    Background task to deauthorize Stripe OAuth connection.
    This runs asynchronously to avoid blocking the disconnect endpoint.
    """
    if not settings.stripe_client_id:
        logger.info(f"Skipping OAuth deauthorization for {stripe_account_id} - no client_id configured")
        return

    try:
        logger.info(f"Deauthorizing Stripe OAuth for account {stripe_account_id} ({business_name})")
        stripe.OAuth.deauthorize(
            client_id=settings.stripe_client_id,
            stripe_user_id=stripe_account_id,
        )
        logger.info(f"Successfully deauthorized Stripe OAuth for account {stripe_account_id}")
    except stripe.error.StripeError as e:
        logger.error(f"Failed to deauthorize Stripe OAuth for account {stripe_account_id}: {str(e)}", exc_info=True)
    except Exception as e:
        logger.error(f"Unexpected error deauthorizing Stripe OAuth for account {stripe_account_id}: {str(e)}", exc_info=True)


def stripe_account_to_response(account: StripeAccount) -> StripeAccountResponse:
    return StripeAccountResponse(
        id=str(account.id),
        stripe_account_id=account.stripe_account_id,
        business_name=account.business_name,
        currency=account.currency,
        country=account.country,
        status=account.status.value,
        connected_at=account.connected_at,
        updated_at=account.updated_at,
    )


async def get_user_workspace(
    workspace_id: str,
    user: User,
    db: AsyncSession,
    required_roles: List[WorkspaceRole] = None,
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
        .options(selectinload(Workspace.members))
        .where(Workspace.id == ws_uuid)
    )
    workspace = result.scalar_one_or_none()

    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found",
        )

    member = next((m for m in workspace.members if m.user_id == user.id), None)

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


@router.get("/connect/start", response_model=StripeConnectStartResponse)
async def start_stripe_connect(
    workspace_id: str = Query(..., description="Workspace ID to connect Stripe account to"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Start Stripe Connect OAuth flow.
    Returns an authorization URL to redirect the user to Stripe.
    """
    workspace = await get_user_workspace(
        workspace_id,
        current_user,
        db,
        required_roles=[WorkspaceRole.OWNER, WorkspaceRole.ADMIN],
    )

    # Generate a secure state token to prevent CSRF
    state = f"{workspace.id}:{secrets.token_urlsafe(32)}"

    # Build OAuth authorization URL
    if settings.stripe_client_id:
        # OAuth flow with read_write access
        # Note: read_only scope requires special Stripe approval and is not available by default
        # We use read_write but only exercise read operations in our application
        params = {
            "response_type": "code",
            "client_id": settings.stripe_client_id,
            "scope": "read_write",  # Standard scope for monitoring platforms
            "redirect_uri": f"{settings.api_url}/api/stripe/connect/callback",
            "state": state,
            "stripe_landing": "register",  # Or "login" - determines Stripe UI flow
        }
        authorization_url = f"https://connect.stripe.com/oauth/authorize?{urlencode(params)}"
    else:
        # For testing: Use Stripe dashboard link
        authorization_url = f"https://dashboard.stripe.com/test/connect/accounts/create"

    return StripeConnectStartResponse(
        authorization_url=authorization_url,
        state=state,
    )


@router.get("/connect/callback")
async def stripe_connect_callback(
    code: str = Query(None),
    state: str = Query(None),
    error: str = Query(None),
    error_description: str = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """
    Handle Stripe Connect OAuth callback.
    Exchanges the authorization code for access tokens and stores the connected account.
    """
    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Stripe Connect error: {error_description or error}",
        )

    if not code or not state:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing code or state parameter",
        )

    # Parse state to get workspace ID
    try:
        workspace_id_str, _ = state.split(":", 1)
        workspace_id = uuid.UUID(workspace_id_str)
    except (ValueError, AttributeError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid state parameter",
        )

    # Verify workspace exists
    result = await db.execute(select(Workspace).where(Workspace.id == workspace_id))
    workspace = result.scalar_one_or_none()

    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found",
        )

    try:
        # Exchange authorization code for access token
        response = stripe.OAuth.token(
            grant_type="authorization_code",
            code=code,
        )

        stripe_account_id = response.get("stripe_user_id")
        access_token = response.get("access_token")
        refresh_token = response.get("refresh_token")

        if not stripe_account_id or not access_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid response from Stripe",
            )

        # Get account details from Stripe
        account = stripe.Account.retrieve(stripe_account_id)

        # Check if account already exists
        existing = await db.execute(
            select(StripeAccount).where(StripeAccount.stripe_account_id == stripe_account_id)
        )
        existing_account = existing.scalar_one_or_none()

        if existing_account:
            # Update existing account
            existing_account.workspace_id = workspace_id
            existing_account.access_token_enc = encrypt_token(access_token)
            if refresh_token:
                existing_account.refresh_token_enc = encrypt_token(refresh_token)
            existing_account.business_name = account.get("business_profile", {}).get("name") or account.get("settings", {}).get("dashboard", {}).get("display_name")
            existing_account.currency = account.get("default_currency", "usd")
            existing_account.country = account.get("country")
            existing_account.status = StripeAccountStatus.CONNECTED
            existing_account.updated_at = datetime.utcnow()
            stripe_acc = existing_account
        else:
            # Create new account
            stripe_acc = StripeAccount(
                workspace_id=workspace_id,
                stripe_account_id=stripe_account_id,
                access_token_enc=encrypt_token(access_token),
                refresh_token_enc=encrypt_token(refresh_token) if refresh_token else None,
                business_name=account.get("business_profile", {}).get("name") or account.get("settings", {}).get("dashboard", {}).get("display_name"),
                currency=account.get("default_currency", "usd"),
                country=account.get("country"),
                status=StripeAccountStatus.CONNECTED,
            )
            db.add(stripe_acc)

        await db.flush()
        await db.refresh(stripe_acc)

        # Return success response (frontend will handle redirect)
        return {"message": "Stripe account connected successfully", "account": stripe_account_to_response(stripe_acc)}

    except stripe.oauth_error.OAuthError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Stripe OAuth error: {str(e)}",
        )
    except stripe.error.StripeError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Stripe error: {str(e)}",
        )


@router.post("/connect/test", response_model=StripeAccountResponse)
async def create_test_stripe_account(
    workspace_id: str = Query(..., description="Workspace ID to connect test account to"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create a test Stripe Connect account for development/testing.
    This bypasses OAuth and creates an account directly using Stripe API.
    Only works in test mode.
    """
    if not settings.stripe_secret_key.startswith("sk_test_"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This endpoint only works in test mode",
        )

    workspace = await get_user_workspace(
        workspace_id,
        current_user,
        db,
        required_roles=[WorkspaceRole.OWNER, WorkspaceRole.ADMIN],
    )

    try:
        # Create a test connected account
        account = stripe.Account.create(
            type="standard",
            country="US",
            email=current_user.email,
        )

        # Store the account
        stripe_acc = StripeAccount(
            workspace_id=workspace.id,
            stripe_account_id=account.id,
            access_token_enc=encrypt_token(settings.stripe_secret_key),  # Use platform key for test accounts
            business_name=account.get("business_profile", {}).get("name"),
            currency=account.get("default_currency", "usd"),
            country=account.get("country", "US"),
            status=StripeAccountStatus.CONNECTED,
        )
        db.add(stripe_acc)
        await db.flush()
        await db.refresh(stripe_acc)

        return stripe_account_to_response(stripe_acc)

    except stripe.error.StripeError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Stripe error: {str(e)}",
        )


@router.get("/accounts", response_model=List[StripeAccountResponse])
async def list_stripe_accounts(
    workspace_id: str = Query(..., description="Workspace ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all connected Stripe accounts for a workspace (excluding deleted accounts)."""
    workspace = await get_user_workspace(workspace_id, current_user, db)

    result = await db.execute(
        select(StripeAccount)
        .where(StripeAccount.workspace_id == workspace.id)
        .where(StripeAccount.deleted_at.is_(None))  # Filter out soft-deleted accounts
        .order_by(StripeAccount.connected_at.desc())
    )
    accounts = result.scalars().all()

    return [stripe_account_to_response(acc) for acc in accounts]


@router.get("/accounts/{account_id}", response_model=StripeAccountResponse)
async def get_stripe_account(
    account_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get details of a connected Stripe account."""
    try:
        acc_uuid = uuid.UUID(account_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid account ID format",
        )

    result = await db.execute(
        select(StripeAccount)
        .options(selectinload(StripeAccount.workspace).selectinload(Workspace.members))
        .where(StripeAccount.id == acc_uuid)
        .where(StripeAccount.deleted_at.is_(None))  # Filter out soft-deleted accounts
    )
    account = result.scalar_one_or_none()

    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Stripe account not found or has been deleted",
        )

    # Verify user has access to the workspace
    member = next((m for m in account.workspace.members if m.user_id == current_user.id), None)
    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this account",
        )

    # Optionally refresh account details from Stripe
    try:
        stripe_account = stripe.Account.retrieve(account.stripe_account_id)
        account.business_name = stripe_account.get("business_profile", {}).get("name") or account.business_name
        account.currency = stripe_account.get("default_currency", account.currency)
        account.country = stripe_account.get("country", account.country)
        account.updated_at = datetime.utcnow()
        await db.flush()
    except stripe.error.StripeError:
        pass  # Use cached data if Stripe call fails

    return stripe_account_to_response(account)


@router.post("/accounts/{account_id}/disconnect")
async def disconnect_stripe_account(
    account_id: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Disconnect (soft delete) a Stripe account from the workspace."""
    try:
        acc_uuid = uuid.UUID(account_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid account ID format",
        )

    result = await db.execute(
        select(StripeAccount)
        .options(selectinload(StripeAccount.workspace).selectinload(Workspace.members))
        .where(StripeAccount.id == acc_uuid)
        .where(StripeAccount.deleted_at.is_(None))  # Only allow disconnecting non-deleted accounts
    )
    account = result.scalar_one_or_none()

    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Stripe account not found or already disconnected",
        )

    # Verify user has admin access to the workspace
    member = next((m for m in account.workspace.members if m.user_id == current_user.id), None)
    if not member or member.role not in [WorkspaceRole.OWNER, WorkspaceRole.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to disconnect this account",
        )

    # Schedule OAuth deauthorization as a background task (non-blocking)
    background_tasks.add_task(
        deauthorize_stripe_oauth,
        account.stripe_account_id,
        account.business_name
    )

    # Soft delete: Set deleted_at and deleted_by
    now = datetime.utcnow()
    account.status = StripeAccountStatus.DISCONNECTED
    account.deleted_at = now
    account.deleted_by = current_user.id
    account.updated_at = now
    await db.flush()

    # Create audit log entry
    audit_entry = AuditLog(
        workspace_id=account.workspace_id,
        user_id=current_user.id,
        action="stripe_account.disconnect",
        resource_type="stripe_account",
        resource_id=str(account.id),
        metadata_json={
            "stripe_account_id": account.stripe_account_id,
            "business_name": account.business_name,
            "country": account.country,
            "currency": account.currency,
            "deleted_at": now.isoformat(),
            "deleted_by_email": current_user.email,
        },
    )
    db.add(audit_entry)
    await db.flush()

    return {"message": "Stripe account disconnected successfully"}


@router.post("/accounts/{account_id}/sync")
async def sync_stripe_account(
    account_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Sync account details from Stripe."""
    try:
        acc_uuid = uuid.UUID(account_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid account ID format",
        )

    result = await db.execute(
        select(StripeAccount)
        .options(selectinload(StripeAccount.workspace).selectinload(Workspace.members))
        .where(StripeAccount.id == acc_uuid)
    )
    account = result.scalar_one_or_none()

    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Stripe account not found",
        )

    # Verify user has access
    member = next((m for m in account.workspace.members if m.user_id == current_user.id), None)
    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this account",
        )

    try:
        stripe_account = stripe.Account.retrieve(account.stripe_account_id)
        account.business_name = stripe_account.get("business_profile", {}).get("name")
        account.currency = stripe_account.get("default_currency", "usd")
        account.country = stripe_account.get("country")
        account.status = StripeAccountStatus.CONNECTED
        account.updated_at = datetime.utcnow()
        await db.flush()
        await db.refresh(account)

        return stripe_account_to_response(account)

    except stripe.error.StripeError as e:
        account.status = StripeAccountStatus.ERROR
        account.updated_at = datetime.utcnow()
        await db.flush()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to sync account: {str(e)}",
        )
