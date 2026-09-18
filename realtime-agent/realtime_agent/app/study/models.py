from enum import Enum
from typing import Optional
from pydantic import BaseModel

class ScreenshotType(str, Enum):
    coding = "coding"
    sql = "sql"
    system_design_diagram = "system_design_diagram"
    ml_chart = "ml_chart"
    math = "math"
    general_question = "general_question"
    unknown = "unknown"

class HintLadder(BaseModel):
    clarify: str
    approach: str
    solution: str

class ClassificationResult(BaseModel):
    screenshot_type: ScreenshotType

class SolverResult(BaseModel):
    id: str
    screenshot_type: ScreenshotType
    hints: HintLadder
    
class StudyItem(BaseModel):
    id: str
    source: str  # e.g., "manual", "screenshot_solve"
    solver_result_id: str
    concept: str
