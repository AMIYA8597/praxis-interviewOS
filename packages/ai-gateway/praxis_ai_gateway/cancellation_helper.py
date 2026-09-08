import asyncio
from typing import Awaitable, TypeVar
from praxis_ai_gateway.cancellation import CancellationToken

T = TypeVar('T')

async def with_cancellation(coro: Awaitable[T], token: CancellationToken | None) -> T:
    if not token:
        return await coro
        
    task = asyncio.create_task(coro)
    wait_task = asyncio.create_task(token.wait_cancelled())
    
    done, pending = await asyncio.wait(
        [task, wait_task],
        return_when=asyncio.FIRST_COMPLETED
    )
    
    if wait_task in done:
        # Cancelled!
        task.cancel()
        raise asyncio.CancelledError(token.reason)
        
    wait_task.cancel()
    return await task
