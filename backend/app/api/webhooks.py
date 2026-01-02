from fastapi import APIRouter, Request

router = APIRouter()


@router.post("/stripe")
async def stripe_webhook(request: Request):
    """Handle incoming Stripe webhooks from connected accounts."""
    pass


@router.post("/billing")
async def billing_webhook(request: Request):
    """Handle MRRPulse billing webhooks."""
    pass
