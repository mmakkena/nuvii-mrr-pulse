from fastapi import APIRouter

router = APIRouter()


@router.get("")
async def list_rules():
    """List all alert rules for the workspace."""
    pass


@router.post("")
async def create_rule():
    """Create a new alert rule."""
    pass


@router.get("/{rule_id}")
async def get_rule(rule_id: str):
    """Get a specific alert rule."""
    pass


@router.put("/{rule_id}")
async def update_rule(rule_id: str):
    """Update an alert rule."""
    pass


@router.delete("/{rule_id}")
async def delete_rule(rule_id: str):
    """Delete an alert rule."""
    pass


@router.post("/presets/{preset_name}")
async def apply_preset(preset_name: str):
    """Apply a preset pack of alert rules."""
    pass
