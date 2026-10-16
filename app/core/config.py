import os
import sys
from dataclasses import dataclass
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Settings:
    env: str = os.getenv("DESANYALA_ENV", "development")
    cors_origins: tuple[str, ...] = tuple(
        item.strip()
        for item in os.getenv(
            "DESANYALA_CORS_ORIGINS",
            "http://localhost:3000,http://127.0.0.1:5500,http://localhost:5500",
        ).split(",")
        if item.strip()
    )
    runs_dir: Path = Path(os.getenv("DESANYALA_RUNS_DIR", str(BACKEND_ROOT / "runs"))).resolve()
    offgridders_root: Path = Path(
        os.getenv("OFFGRIDDERS_ROOT", str(BACKEND_ROOT / "engine" / "offgridders"))
    ).resolve()
    # Use the Offgridders environment if its dependencies/solver are installed there.
    offgridders_python: str = os.getenv("OFFGRIDDERS_PYTHON", sys.executable)
    offgridders_timeout_seconds: int = int(os.getenv("OFFGRIDDERS_TIMEOUT_SECONDS", "1200"))


settings = Settings()
