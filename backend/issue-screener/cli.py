# cli.py
from __future__ import annotations
import argparse
from loguru import logger

from services.topic_service import TopicService
from services.screener_gemini import gemini_screener  # ✅ 추가

def parse_args():
    p = argparse.ArgumentParser(description="Process NEW topics and update statuses.")
    p.add_argument("--once", action="store_true", help="1건만 처리하고 종료")
    p.add_argument("--max-items", type=int, default=50, help="(배치) 최대 처리 개수")
    p.add_argument("--sleep", type=float, default=0.2, help="(배치) 항목 간 대기 시간(초)")
    return p.parse_args()

def main():
    args = parse_args()
    svc = TopicService()

    if args.once:
        stats = svc.process_one(screener=gemini_screener, sleep_between_items=args.sleep)  # ✅ 변경
        logger.info(
            f"처리 완료 | processed={stats['processed']} skipped={stats['skipped']} "
            f"claimed={stats['claimed']} conflict={stats['conflict']}"
        )
    else:
        total = {"processed": 0, "skipped": 0, "claimed": 0, "posted": 0, "conflict": 0}
        for _ in range(args.max_items):
            stats = svc.process_one(screener=gemini_screener, sleep_between_items=args.sleep)  # ✅ 변경
            if sum(stats.values()) == 0:
                break
            for k in total:
                total[k] += stats[k]
        logger.info(
            f"[배치] 처리 완료 | processed={total['processed']} skipped={total['skipped']} "
            f"claimed={total['claimed']} conflict={total['conflict']}"
        )

if __name__ == "__main__":
    main()
