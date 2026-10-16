from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.health import router as health_router
from app.api.routes.inputs import router as inputs_router
from app.api.routes.optimizations import router as optimizations_router
from app.core.config import settings
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="DesaNyala API",
    version="0.1.0",
    description=(
        "Backend API for PV + diesel generator + optional battery planning. "
        "The optimizer runs only after an Offgridders source checkout has been imported and verified."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://desanyala-fe.vercel.app",
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(inputs_router, prefix="/api/v1")
app.include_router(optimizations_router, prefix="/api/v1")
