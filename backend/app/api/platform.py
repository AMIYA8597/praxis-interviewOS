from fastapi import APIRouter
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/resume/generate")
async def generate_resume():
    """Delegates to Resume Builder service."""
    pass

@router.post("/outreach/generate")
async def generate_outreach():
    """Delegates to Cold Outreach service."""
    pass

@router.get("/applications")
async def list_applications():
    """CRUD: List applications."""
    pass
