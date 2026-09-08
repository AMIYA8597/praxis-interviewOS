import logging
import asyncio
from pydantic import BaseModel

from packages.ai_gateway.router import GatewayRouter, RoutingContext
from app.ai.prompt_builder import PromptBuilder

logger = logging.getLogger(__name__)

class ExtractionSchema(BaseModel):
    # Stub representing the complex Pydantic schema required for structured output
    skills: list[str]
    experiences: list[dict]
    projects: list[dict]
    education: list[dict]

async def process_resume(ctx, resume_id: str, file_uri: str):
    """
    ARQ worker task to:
    1. Parse PDF via pdfplumber
    2. Prompt AI Gateway using reasoning alias for structured output
    3. Save facts with verified_by_user = false
    4. Trigger Chunking & Embedding
    """
    logger.info(f"Worker started extracting resume: {resume_id}")
    
    # 1. Parse (stub)
    raw_text = "Extracted text from PDF"
    
    # 2. Build Prompt defensively
    builder = PromptBuilder()
    builder.set_system_instructions("Extract candidate facts strictly matching the schema.")
    builder.add_untrusted_document(raw_text, source="resume")
    prompt = builder.build()
    
    # 3. AI Execution
    gateway = GatewayRouter()
    provider = gateway.route("reasoning", RoutingContext())
    
    # In a real run, this calls the LLM via structured JSON mode
    # result = await provider.structured([{"role": "user", "content": prompt}], ExtractionSchema)
    
    # 4. Save to DB with verified_by_user = False
    # (Insert into CandidateSkills, CandidateExperiences, etc.)
    logger.info("Extraction complete. Facts saved pending user verification.")
    
    # 5. Chunking & Embedding
    # await embed_chunks(resume_id, raw_text)
