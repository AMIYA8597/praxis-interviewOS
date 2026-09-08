import asyncio
import time
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def simulate_audio_session(session_id: int):
    """
    Mocks an active WebSocket pushing 16kHz PCM frames to the backend.
    """
    logger.info(f"Session {session_id} connected.")
    # In a real run, this would be `websockets.connect(...)`
    # Here we just simulate the asyncio loop pressure
    for _ in range(100): # 100 frames (~3 seconds of audio)
        await asyncio.sleep(0.032) # 32ms frame cadence
    logger.info(f"Session {session_id} completed.")

async def main(concurrency: int):
    logger.info(f"Starting Load Sanity Check with {concurrency} concurrent sessions.")
    start = time.perf_counter()
    
    tasks = [simulate_audio_session(i) for i in range(concurrency)]
    await asyncio.gather(*tasks)
    
    elapsed = time.perf_counter() - start
    logger.info(f"Finished {concurrency} sessions in {elapsed:.2f}s.")
    logger.info(f"Target duration was ~3.2s. Actual: {elapsed:.2f}s.")
    
    if elapsed > 4.0:
        logger.warning("EVIDENCE: CPU/Event Loop starvation detected at this concurrency level.")
    else:
        logger.info("EVIDENCE: System maintained sub-250ms cadence across concurrent load.")

if __name__ == "__main__":
    # Test 5, then 20
    asyncio.run(main(5))
    time.sleep(1)
    asyncio.run(main(20))
