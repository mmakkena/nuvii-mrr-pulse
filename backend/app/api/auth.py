import uuid
import random
import string
import re
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models import User
from app.models.workspace import Workspace, WorkspacePlan, WorkspaceMember, WorkspaceRole
from app.services.email_service import send_template_email
from app.models.email_template import EmailTemplateType
from app.schemas import (
    UserCreate,
    UserLogin,
    UserResponse,
    TokenResponse,
    RefreshTokenRequest,
    AuthResponse,
)
from app.utils.auth import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
    get_current_user,
)
from app.config import settings
from app.services.email_service import send_otp_email, send_welcome_email

router = APIRouter()

# OTP expiry time in minutes
OTP_EXPIRY_MINUTES = 10


def utc_now() -> datetime:
    """Get current UTC time as timezone-aware datetime."""
    return datetime.now(timezone.utc)


def generate_otp() -> str:
    """Generate a 6-digit OTP code."""
    return ''.join(random.choices(string.digits, k=6))


def generate_workspace_slug(name: str, user_id: uuid.UUID) -> str:
    """Generate a unique workspace slug from name."""
    slug = name.lower()
    slug = re.sub(r'[^a-z0-9]+', '-', slug)
    slug = slug.strip('-')
    return f"{slug}-{str(user_id)[:8]}"


# Additional schemas for auth
class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


class GoogleAuthRequest(BaseModel):
    id_token: str


class AcceptInvitationRequest(BaseModel):
    token: str
    password: str
    name: str = None  # Optional: user can update their name


def user_to_response(user: User) -> UserResponse:
    return UserResponse(
        id=str(user.id),
        email=user.email,
        name=user.name,
        avatar_url=user.avatar_url,
        email_verified=user.email_verified,
        roles=user.roles or ["user"],
        created_at=user.created_at,
    )


def create_password_reset_token(user_id: uuid.UUID) -> str:
    """Create a password reset token valid for 1 hour."""
    from jose import jwt
    expire = datetime.utcnow() + timedelta(hours=1)
    to_encode = {
        "sub": str(user_id),
        "exp": expire,
        "type": "password_reset",
    }
    return jwt.encode(to_encode, settings.jwt_secret, algorithm=settings.jwt_algorithm)


class VerifyOtpRequest(BaseModel):
    email: EmailStr
    otp: str


class ResendOtpRequest(BaseModel):
    email: EmailStr


class SignupResponse(BaseModel):
    message: str
    email: str
    requires_verification: bool = True


@router.post("/signup", response_model=SignupResponse)
async def signup(data: UserCreate, db: AsyncSession = Depends(get_db)):
    """Register a new user with email and password. Sends OTP for verification."""
    result = await db.execute(select(User).where(User.email == data.email))
    existing_user = result.scalar_one_or_none()

    if existing_user:
        # If user exists but email not verified, allow re-registration (resend OTP)
        if not existing_user.email_verified:
            otp_code = generate_otp()
            existing_user.otp_code = otp_code
            existing_user.otp_expires_at = utc_now() + timedelta(minutes=OTP_EXPIRY_MINUTES)
            existing_user.password_hash = hash_password(data.password)
            existing_user.name = data.name
            await db.commit()

            # Send OTP email
            await send_otp_email(existing_user.email, otp_code, existing_user.name)

            return SignupResponse(
                message="Verification code sent to your email",
                email=data.email,
                requires_verification=True,
            )

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    # Generate OTP
    otp_code = generate_otp()

    # Create user (not verified yet)
    user = User(
        email=data.email,
        password_hash=hash_password(data.password),
        name=data.name,
        email_verified=False,
        otp_code=otp_code,
        otp_expires_at=utc_now() + timedelta(minutes=OTP_EXPIRY_MINUTES),
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)

    # Create default workspace for the user
    workspace_name = data.workspace_name if data.workspace_name else f"{data.name}'s Workspace"
    workspace = Workspace(
        name=workspace_name,
        slug=generate_workspace_slug(workspace_name, user.id),
        owner_id=user.id,
        plan=WorkspacePlan.STARTER,
    )
    db.add(workspace)
    await db.flush()
    await db.refresh(workspace)

    # Add user as workspace owner
    member = WorkspaceMember(
        workspace_id=workspace.id,
        user_id=user.id,
        role=WorkspaceRole.OWNER,
        invited_at=utc_now(),
        joined_at=utc_now(),
    )
    db.add(member)

    await db.commit()

    # Send OTP email
    await send_otp_email(user.email, otp_code, user.name)

    return SignupResponse(
        message="Account created! Please check your email for the verification code",
        email=data.email,
        requires_verification=True,
    )


@router.post("/verify-otp", response_model=AuthResponse)
async def verify_otp(data: VerifyOtpRequest, db: AsyncSession = Depends(get_db)):
    """Verify OTP code and complete registration."""
    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    if user.email_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already verified",
        )

    if not user.otp_code or not user.otp_expires_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No verification code found. Please request a new one.",
        )

    if utc_now() > user.otp_expires_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification code has expired. Please request a new one.",
        )

    if user.otp_code != data.otp:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification code",
        )

    # Mark email as verified and clear OTP
    user.email_verified = True
    user.otp_code = None
    user.otp_expires_at = None
    user.updated_at = datetime.utcnow()

    await db.commit()
    await db.refresh(user)

    # Send welcome email (non-blocking)
    await send_welcome_email(user.email, user.name)

    # Create tokens and return auth response
    access_token = create_access_token(user.id)
    refresh_token = create_refresh_token(user.id)

    return AuthResponse(
        user=user_to_response(user),
        tokens=TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
        ),
    )


@router.post("/resend-otp")
async def resend_otp(data: ResendOtpRequest, db: AsyncSession = Depends(get_db)):
    """Resend OTP verification code."""
    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()

    if not user:
        # Don't reveal if email exists or not
        return {"message": "If your email is registered, a verification code has been sent."}

    if user.email_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already verified",
        )

    # Generate new OTP
    otp_code = generate_otp()
    user.otp_code = otp_code
    user.otp_expires_at = utc_now() + timedelta(minutes=OTP_EXPIRY_MINUTES)

    await db.commit()

    # Send OTP email
    await send_otp_email(user.email, otp_code, user.name)

    return {"message": "If your email is registered, a verification code has been sent."}


@router.post("/login", response_model=AuthResponse)
async def login(data: UserLogin, db: AsyncSession = Depends(get_db)):
    """Authenticate user and return JWT tokens."""
    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()

    if not user or not user.password_hash:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not verify_password(data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    access_token = create_access_token(user.id)
    refresh_token = create_refresh_token(user.id)

    return AuthResponse(
        user=user_to_response(user),
        tokens=TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
        ),
    )


@router.post("/logout")
async def logout():
    """Invalidate the current session."""
    return {"message": "Logged out successfully"}


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """Get the current authenticated user."""
    return user_to_response(current_user)


@router.post("/google", response_model=AuthResponse)
async def google_oauth(data: GoogleAuthRequest, db: AsyncSession = Depends(get_db)):
    """Handle Google OAuth - verify ID token and create/login user."""
    import httpx

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"https://oauth2.googleapis.com/tokeninfo?id_token={data.id_token}"
        )

    if response.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Google ID token",
        )

    google_data = response.json()

    if google_data.get("aud") != settings.google_client_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token not issued for this application",
        )

    google_id = google_data.get("sub")
    email = google_data.get("email")
    name = google_data.get("name", email.split("@")[0])
    picture = google_data.get("picture")

    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email not provided by Google",
        )

    result = await db.execute(select(User).where(User.google_id == google_id))
    user = result.scalar_one_or_none()

    if not user:
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

        if user:
            user.google_id = google_id
            if picture and not user.avatar_url:
                user.avatar_url = picture
            user.email_verified = True
        else:
            user = User(
                email=email,
                name=name,
                google_id=google_id,
                avatar_url=picture,
                email_verified=True,
            )
            db.add(user)

    await db.flush()
    await db.refresh(user)

    access_token = create_access_token(user.id)
    refresh_token = create_refresh_token(user.id)

    return AuthResponse(
        user=user_to_response(user),
        tokens=TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
        ),
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(data: RefreshTokenRequest, db: AsyncSession = Depends(get_db)):
    """Refresh the access token."""
    payload = decode_token(data.refresh_token)

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
        )

    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    new_access_token = create_access_token(user.id)
    new_refresh_token = create_refresh_token(user.id)

    return TokenResponse(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
    )


@router.post("/forgot-password")
async def forgot_password(data: ForgotPasswordRequest, db: AsyncSession = Depends(get_db)):
    """Initiate password reset - generates reset token."""
    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()

    if not user:
        return {"message": "If the email exists, a password reset link has been sent"}

    reset_token = create_password_reset_token(user.id)

    if settings.debug:
        return {
            "message": "Password reset token generated",
            "reset_token": reset_token,
            "reset_url": f"{settings.frontend_url}/reset-password?token={reset_token}",
        }

    return {"message": "If the email exists, a password reset link has been sent"}


@router.post("/reset-password")
async def reset_password(data: ResetPasswordRequest, db: AsyncSession = Depends(get_db)):
    """Complete password reset using the reset token."""
    payload = decode_token(data.token)

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )

    if payload.get("type") != "password_reset":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid token type",
        )

    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid token payload",
        )

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    if len(data.new_password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters",
        )

    user.password_hash = hash_password(data.new_password)
    user.updated_at = datetime.utcnow()

    await db.flush()

    return {"message": "Password reset successfully"}


@router.post("/accept-invitation", response_model=AuthResponse)
async def accept_invitation(data: AcceptInvitationRequest, db: AsyncSession = Depends(get_db)):
    """Accept workspace invitation by setting password and completing registration."""

    # Find workspace member by invitation token
    result = await db.execute(
        select(WorkspaceMember)
        .where(WorkspaceMember.invitation_token == data.token)
        .options(selectinload(WorkspaceMember.user))
        .options(selectinload(WorkspaceMember.workspace))
    )
    member = result.scalar_one_or_none()

    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid invitation token",
        )

    # Check if invitation has already been accepted
    if member.joined_at is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invitation has already been accepted",
        )

    # Check if invitation has expired
    if member.token_expires_at and utc_now() > member.token_expires_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invitation has expired",
        )

    # Validate password
    if len(data.password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters",
        )

    # Get the user
    user = member.user

    # Update user: set password, verify email, optionally update name
    user.password_hash = hash_password(data.password)
    user.email_verified = True
    if data.name:
        user.name = data.name
    user.updated_at = datetime.utcnow()

    # Update membership: mark as joined, clear invitation token
    member.joined_at = utc_now()
    member.invitation_token = None
    member.token_expires_at = None

    await db.commit()
    await db.refresh(user)
    await db.refresh(member)

    # Send welcome email
    await send_template_email(
        db=db,
        to_email=user.email,
        template_type=EmailTemplateType.WELCOME,
        variables={
            "user_name": user.name,
            "dashboard_url": f"{settings.frontend_url}/dashboard",
        },
        workspace_id=member.workspace_id
    )

    # Create auth tokens
    access_token = create_access_token(user.id)
    refresh_token = create_refresh_token(user.id)

    return AuthResponse(
        user=user_to_response(user),
        tokens=TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
        ),
    )
