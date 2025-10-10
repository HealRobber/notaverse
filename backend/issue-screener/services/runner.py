#!/usr/bin/env python3
from __future__ import annotations

import threading
import time
from typing import Optional, Callable, Dict

from loguru import logger

from services.topic_service import TopicService


class RunnerManager:
    """TopicService 무한 루프를 스레드로 제어하는 매니저"""

    def __init__(self, service: Optional[TopicService] = None):
        self.service = service or TopicService()
        self._thread: Optional[threading.Thread] = None
        self._stop_event: Optional[threading.Event] = None
        self._lock = threading.Lock()
        self._state = "stopped"  # "running" | "stopping" | "stopped"
        self._started_at: Optional[float] = None
        self._stopped_at: Optional[float] = None
        self._last_error: Optional[str] = None

    def start(
        self,
        screener: Callable[[str, Optional[str]], Dict],
        idle_min_sec: float = 2.0,
        idle_max_sec: float = 60.0,
    ) -> bool:
        with self._lock:
            if self._state == "running" and self._thread and self._thread.is_alive():
                return False  # 이미 실행 중

            self._stop_event = threading.Event()
            self._state = "running"
            self._started_at = time.time()
            self._stopped_at = None
            self._last_error = None

            def _target():
                try:
                    self.service.process_loop_forever(
                        screener=screener,
                        stop_event=self._stop_event,
                        idle_min_sec=idle_min_sec,
                        idle_max_sec=idle_max_sec,
                    )
                except Exception as e:
                    logger.exception("Runner thread crashed")
                    self._last_error = str(e)
                finally:
                    with self._lock:
                        self._state = "stopped"
                        self._stopped_at = time.time()

            self._thread = threading.Thread(target=_target, name="TopicRunner", daemon=True)
            self._thread.start()
            return True

    def stop(self) -> bool:
        with self._lock:
            if self._state != "running" or not self._stop_event:
                return False
            self._state = "stopping"
            self._stop_event.set()
        # 스레드 합류 대기(비차단적으로 짧게 반복)
        for _ in range(100):
            t = self._thread
            if not t:
                break
            t.join(timeout=0.1)
            if not t.is_alive():
                break
        with self._lock:
            self._state = "stopped"
            self._stopped_at = time.time()
        return True

    def status(self) -> dict:
        with self._lock:
            alive = bool(self._thread and self._thread.is_alive())
            return {
                "state": "running" if alive else self._state,
                "started_at": self._started_at,
                "stopped_at": self._stopped_at,
                "last_error": self._last_error,
                "thread_alive": alive,
            }

# 애플리케이션 전역 싱글톤
runner_manager = RunnerManager()
