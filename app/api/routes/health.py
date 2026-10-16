from app.core.config import settings
from fastapi import APIRouter

router = APIRouter(tags=["system"])


@router.get("/health")
def health() -> dict[str, str | bool]:
    engine_ready = (settings.offgridders_root / "Offgridders.py").is_file() and (settings.offgridders_root / "src").is_dir()
    return {
        "status": "ok",
        "service": "desanyala-backend",
        "optimization_engine": "ready" if engine_ready else "not_imported",
        "engine_path": str(settings.offgridders_root),
    }
