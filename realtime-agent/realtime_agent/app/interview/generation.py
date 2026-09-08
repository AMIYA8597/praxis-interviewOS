import uuid
from typing import Optional
from dataclasses import dataclass
from praxis_ai_gateway.cancellation import CancellationToken

@dataclass
class GenerationContext:
    generation_id: str
    turn_id: str
    token: CancellationToken

class SessionGenerationManager:
    def __init__(self):
        self.current_context: Optional[GenerationContext] = None
        
    def start_generation(self, turn_id: str) -> GenerationContext:
        """Starts a new generation, cancelling any existing one."""
        if self.current_context and not self.current_context.token.is_cancelled():
            self.current_context.token.cancel("superseded")
            
        gen_id = str(uuid.uuid4())
        ctx = GenerationContext(
            generation_id=gen_id,
            turn_id=turn_id,
            token=CancellationToken()
        )
        self.current_context = ctx
        return ctx
        
    def cancel_current(self, reason: str):
        """Cancels the current generation explicitly."""
        if self.current_context and not self.current_context.token.is_cancelled():
            self.current_context.token.cancel(reason)
            
    def is_current(self, generation_id: str) -> bool:
        """Check if a given generation is still the current valid one."""
        if not self.current_context:
            return False
        return self.current_context.generation_id == generation_id
