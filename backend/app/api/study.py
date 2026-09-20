from fastapi import APIRouter, Depends, Request
from typing import List, Dict, Any
from pydantic import BaseModel
from backend.app.dependencies import get_current_candidate, get_ai_gateway

router = APIRouter(tags=["study"])

class GenerateMaterialRequest(BaseModel):
    topic: str
    difficulty: str

class SolveScreenshotRequest(BaseModel):
    image_base64: str
    screenshot_task_id: str

@router.get("/study/materials")
async def get_study_materials(
    candidate: dict = Depends(get_current_candidate),
    gateway = Depends(get_ai_gateway)
):
    from sqlalchemy import text
    query = text("""
        SELECT id, topic, source, prompt, reference_answer, difficulty, created_at, next_review_at
        FROM study_items 
        WHERE candidate_id = :cid 
        ORDER BY created_at DESC
    """)
    res = await gateway.db.execute(query, {"cid": candidate["id"]})
    rows = res.fetchall()
    return {"materials": [dict(r._mapping) for r in rows]}

@router.post("/study/generate")
async def generate_study_material(
    req: GenerateMaterialRequest, 
    request: Request,
    candidate: dict = Depends(get_current_candidate)
):
    import uuid
    task_id = str(uuid.uuid4())
    if hasattr(request.app.state, 'arq_pool'):
        await request.app.state.arq_pool.enqueue_job(
            "generate_study_material_job", 
            req.topic, 
            req.difficulty, 
            candidate["id"], 
            task_id
        )
    return {"status": "queued", "task_id": task_id}

@router.post("/study/screenshots/solve")
async def solve_screenshot_endpoint(
    req: SolveScreenshotRequest, 
    candidate: dict = Depends(get_current_candidate),
    gateway = Depends(get_ai_gateway)
):
    from realtime_agent.app.study.solver import solve_screenshot
    from praxis_ai_gateway.router import RoutingContext
    import base64
    from praxis_ai_gateway.vision.ocr_pipeline import process_screenshot_hybrid
    
    ctx = RoutingContext(user_id=candidate["profile_id"], session_id=req.screenshot_task_id)
    
    # Extract base64 part if it contains the data URI scheme
    b64_str = req.image_base64
    if "," in b64_str:
        b64_str = b64_str.split(",", 1)[1]
    image_bytes = base64.b64decode(b64_str)
    
    analysis = await process_screenshot_hybrid(image_bytes, gateway, ctx)
    extracted_text = analysis.extracted_text
    
    result = await solve_screenshot(extracted_text, req.screenshot_task_id, gateway, ctx)
    return result

@router.post("/study/items/from-solve/{solver_result_id}")
async def create_item_from_solve(
    solver_result_id: str,
    candidate: dict = Depends(get_current_candidate),
    gateway = Depends(get_ai_gateway)
):
    from realtime_agent.app.study.solver import create_study_item_from_solve
    result = await create_study_item_from_solve(solver_result_id, candidate["id"], gateway.db)
    return result

@router.get("/study/items/due")
async def get_due_items(
    candidate: dict = Depends(get_current_candidate),
    gateway = Depends(get_ai_gateway)
):
    from sqlalchemy import text
    query = text("""
        SELECT id, topic, source, prompt, reference_answer, difficulty, created_at
        FROM study_items 
        WHERE candidate_id = :cid 
        AND (next_review_at IS NULL OR next_review_at <= now())
        ORDER BY created_at ASC
        LIMIT 10
    """)
    res = await gateway.db.execute(query, {"cid": candidate["id"]})
    rows = res.fetchall()
    return {"items": [dict(r._mapping) for r in rows]}

class ReviewItemRequest(BaseModel):
    quality: int

@router.post("/study/items/{item_id}/review")
async def review_study_item(
    item_id: str,
    req: ReviewItemRequest,
    candidate: dict = Depends(get_current_candidate),
    gateway = Depends(get_ai_gateway)
):
    from sqlalchemy import text
    from backend.app.services.sm2 import calculate_sm2
    import datetime
    
    # fetch existing item
    query = text("SELECT ease_factor, interval_days, COALESCE(repetitions, 0) as reps FROM study_items WHERE id = :id AND candidate_id = :cid")
    res = await gateway.db.execute(query, {"id": item_id, "cid": candidate["id"]})
    row = res.fetchone()
    if not row:
        return {"error": "Item not found"}
        
    ef, interval, reps = row
    
    new_interval, new_reps, new_ef = calculate_sm2(req.quality, int(reps), float(interval), float(ef))
    
    # next_review_at = now + new_interval days
    next_review = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=new_interval)
    
    update_q = text("""
        UPDATE study_items 
        SET ease_factor = :ef, 
            interval_days = :interval, 
            repetitions = :reps,
            next_review_at = :next_review
        WHERE id = :id
    """)
    await gateway.db.execute(update_q, {
        "ef": new_ef,
        "interval": new_interval,
        "reps": new_reps,
        "next_review": next_review,
        "id": item_id
    })
    await gateway.db.commit()
    
    return {"status": "success", "next_review_at": next_review}
