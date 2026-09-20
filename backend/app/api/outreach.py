from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import List
from backend.app.dependencies import get_current_candidate, get_ai_gateway
from backend.app.services.outreach import generate_cold_outreach
from praxis_ai_gateway.router import RoutingContext

router = APIRouter(tags=["outreach"])

class CampaignCreate(BaseModel):
    company: str
    detail: str

@router.get("/outreach/campaigns")
async def list_campaigns(candidate: dict = Depends(get_current_candidate)):
    return {"campaigns": []}

@router.post("/outreach/draft")
async def draft_outreach(
    req: CampaignCreate, 
    candidate: dict = Depends(get_current_candidate),
    gateway = Depends(get_ai_gateway)
):
    ctx = RoutingContext(user_id=candidate["profile_id"])
    draft = await generate_cold_outreach(
        candidate_id=candidate["id"],
        company=req.company,
        detail=req.detail,
        gateway_router=gateway,
        routing_ctx=ctx
    )
    return {"status": "success", "draft": draft}
