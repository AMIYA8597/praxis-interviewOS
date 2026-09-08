import asyncio
from typing import Optional

class CancellationToken:
    def __init__(self):
        self._event = asyncio.Event()
        self.reason: Optional[str] = None
        
    def cancel(self, reason: str) -> None:
        self.reason = reason
        self._event.set()
        
    def is_cancelled(self) -> bool:
        return self._event.is_set()
        
    async def wait_cancelled(self) -> None:
        await self._event.wait()
