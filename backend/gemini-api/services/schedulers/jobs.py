import asyncio
import logging
from typing import Dict

logger = logging.getLogger(__name__)

async def example_batch(params: Dict) -> Dict:
    topic = params.get("topic", "default")
    count = int(params.get("count", 1))
    logger.info("[START] example_batch topic=%s count=%s", topic, count)
    for i in range(count):
        await asyncio.sleep(0.2)
        logger.info("processed %s/%s (%s)", i + 1, count, topic)
    result = {"status": "ok", "processed": count, "topic": topic}
    logger.info("[DONE] example_batch result=%s", result)
    return result

async def image_cleanup(params: Dict) -> Dict:
    days = int(params.get("days", 7))
    logger.info("[START] image_cleanup days=%s", days)
    await asyncio.sleep(0.5)
    deleted = 42  # 예시
    result = {"status": "ok", "deleted": deleted, "older_than_days": days}
    logger.info("[DONE] image_cleanup result=%s", result)
    return result
