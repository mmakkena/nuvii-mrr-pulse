from fastapi import APIRouter

router = APIRouter()


@router.get("/subscription")
async def get_subscription():
    """Get current subscription status."""
    pass


@router.post("/checkout")
async def create_checkout_session():
    """Create a Stripe Checkout session for subscription."""
    pass


@router.get("/portal")
async def get_billing_portal():
    """Get Stripe Customer Portal URL."""
    pass


@router.get("/invoices")
async def list_invoices():
    """List billing invoices."""
    pass


@router.get("/usage")
async def get_usage():
    """Get current usage metrics (accounts, alerts, etc.)."""
    pass
