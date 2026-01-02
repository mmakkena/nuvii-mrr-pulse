from fastapi import APIRouter

router = APIRouter()


@router.post("/signup")
async def signup():
    """Register a new user with email and password."""
    pass


@router.post("/login")
async def login():
    """Authenticate user and return JWT tokens."""
    pass


@router.post("/logout")
async def logout():
    """Invalidate the current session."""
    pass


@router.get("/me")
async def get_current_user():
    """Get the current authenticated user."""
    pass


@router.post("/google")
async def google_oauth():
    """Handle Google OAuth callback."""
    pass


@router.post("/refresh")
async def refresh_token():
    """Refresh the access token."""
    pass


@router.post("/forgot-password")
async def forgot_password():
    """Initiate password reset."""
    pass


@router.post("/reset-password")
async def reset_password():
    """Complete password reset."""
    pass
