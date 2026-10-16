from fastapi import APIRouter
from app.schemas.input import OptimizationRequest
from app.services.validation import validate_request_summary

router = APIRouter(prefix="/inputs", tags=["inputs"])


@router.post("/validate")
def validate_inputs(request: OptimizationRequest) -> dict:
    """Validate the frontend contract and calculate a simple daily energy estimate."""
    return validate_request_summary(request)
