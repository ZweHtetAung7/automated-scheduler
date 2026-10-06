from fastapi import APIRouter

from app.scheduler.defaults import DEFAULT_SETTINGS

router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/settings/defaults")
def settings_defaults() -> dict[str, object]:
    """Every customizable setting with its default value (docs/customization.md)."""
    return DEFAULT_SETTINGS
