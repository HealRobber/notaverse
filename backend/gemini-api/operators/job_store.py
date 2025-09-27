from __future__ import annotations
import json, time, uuid, asyncio
from typing import Dict, Optional, Any, Literal
from dataclasses import dataclass, field

try:
    import redis  # 선택
except ImportError:
    redis = None

Status = Literal["queued", "running", "done", "error"]

@dataclass
class JobState:
    status: Status = "queued"
    steps: Dict[str, str] = field(default_factory=dict)
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    started_at: float = field(default_factory=time.time)
    finished_at: Optional[float] = None

class JobStore:
    def __init__(self, redis_url: Optional[str] = None):
        self._mem: Dict[str, JobState] = {}
        self._r = redis.Redis.from_url(redis_url) if (redis_url and redis) else None

    def new_job(self) -> str:
        jid = uuid.uuid4().hex
        self.set(jid, JobState())
        return jid

    def set(self, jid: str, st: JobState) -> None:
        if self._r:
            self._r.setex(f"job:{jid}", 3600, json.dumps({
                "status": st.status, "steps": st.steps, "result": st.result,
                "error": st.error, "started_at": st.started_at, "finished_at": st.finished_at,
            }))
        else:
            self._mem[jid] = st

    def get(self, jid: str) -> Optional[JobState]:
        if self._r:
            raw = self._r.get(f"job:{jid}")
            if not raw: return None
            d = json.loads(raw)
            st = JobState(
                status=d["status"], steps=d["steps"], result=d.get("result"),
                error=d.get("error"), started_at=d["started_at"], finished_at=d.get("finished_at"),
            )
            return st
        return self._mem.get(jid)

    def update(self, jid: str, **kwargs) -> None:
        st = self.get(jid);
        if not st: return
        for k, v in kwargs.items():
            if k == "steps" and isinstance(v, dict):
                st.steps.update(v)
            else:
                setattr(st, k, v)
        self.set(jid, st)

job_store = JobStore(redis_url=None)  # settings.redis_url 사용 가능
