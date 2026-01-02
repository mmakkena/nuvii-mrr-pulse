from fastapi import APIRouter

router = APIRouter()


@router.get("/connect/start")
async def start_stripe_connect():
    """Start Stripe Connect OAuth flow."""
    pass


@router.get("/connect/callback")
async def stripe_connect_callback():
    """Handle Stripe Connect OAuth callback."""
    pass


@router.get("/accounts")
async def list_stripe_accounts():
    """List connected Stripe accounts."""
    pass


@router.get("/accounts/{account_id}")
async def get_stripe_account(account_id: str):
    """Get details of a connected Stripe account."""
    pass


@router.post("/accounts/{account_id}/disconnect")
async def disconnect_stripe_account(account_id: str):
    """Disconnect a Stripe account."""
    pass
