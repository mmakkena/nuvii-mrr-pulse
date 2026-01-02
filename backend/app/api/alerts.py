from fastapi import APIRouter

router = APIRouter()


@router.get("")
async def list_alerts():
    """List alerts with optional filters."""
    pass


@router.get("/{alert_id}")
async def get_alert(alert_id: str):
    """Get a specific alert."""
    pass


@router.post("/{alert_id}/acknowledge")
async def acknowledge_alert(alert_id: str):
    """Mark an alert as acknowledged."""
    pass


@router.post("/test")
async def send_test_alert():
    """Send a test alert to configured channels."""
    pass
