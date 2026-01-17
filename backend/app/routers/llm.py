"""LLM endpoints for generating human-friendly explanations."""

from fastapi import APIRouter, Depends, HTTPException, status, Cookie
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel

from app.services import gemini_service
from app.routers.auth import verify_token

router = APIRouter()


# Pydantic models
class RiskExplanationRequest(BaseModel):
    probability: int
    reasons: List[str]


class FinalSummaryRequest(BaseModel):
    savings: int  # in cents
    count: int
    alerts_avoided: int


class TextResponse(BaseModel):
    text: str


async def get_current_user_id(
    access_token: Optional[str] = Cookie(default=None),
) -> UUID:
    """Get current user ID from token."""
    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    payload = verify_token(access_token)
    if payload is None or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    return UUID(payload["sub"])


@router.post("/risk-explain", response_model=TextResponse)
async def explain_risk(
    request: RiskExplanationRequest,
    user_id: UUID = Depends(get_current_user_id),
):
    """Generate human-friendly explanation for non-use risk prediction."""
    try:
        text = await gemini_service.generate_risk_narrative(
            probability=request.probability,
            reasons=request.reasons,
        )
        return TextResponse(text=text)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate explanation: {str(e)}",
        )


@router.post("/final-summary", response_model=TextResponse)
async def generate_summary(
    request: FinalSummaryRequest,
    user_id: UUID = Depends(get_current_user_id),
):
    """Generate motivational summary for demo ending."""
    try:
        text = await gemini_service.generate_final_summary(
            savings=request.savings,
            count=request.count,
            alerts_avoided=request.alerts_avoided,
        )
        return TextResponse(text=text)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate summary: {str(e)}",
        )
