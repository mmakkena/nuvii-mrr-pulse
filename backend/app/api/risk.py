from fastapi import APIRouter

router = APIRouter()


@router.get("/status")
async def get_risk_status():
    """Get current risk status for the workspace."""
    pass


@router.get("/status/{account_id}")
async def get_account_risk_status(account_id: str):
    """Get risk status for a specific Stripe account."""
    pass


@router.get("/history")
async def get_risk_history():
    """Get risk metrics history."""
    pass


@router.get("/thresholds")
async def get_risk_thresholds():
    """Get configured risk thresholds."""
    pass


@router.put("/thresholds")
async def update_risk_thresholds():
    """Update risk thresholds."""
    pass
