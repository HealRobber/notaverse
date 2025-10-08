from typing import Awaitable, Callable, Dict
from services.schedulers.jobs import example_batch, image_cleanup

JobFunc = Callable[[dict], Awaitable[dict]]

REGISTRY: Dict[str, JobFunc] = {
    "example.batch": example_batch,
    "image.cleanup": image_cleanup,
}
