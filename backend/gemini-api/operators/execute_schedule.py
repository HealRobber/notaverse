import asyncio
import json
import logging
import os
import sys
import argparse

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
APP_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
if APP_ROOT not in sys.path:
    sys.path.insert(0, APP_ROOT)

from services.schedulers.scheduler import start_scheduler, run_now

logging.basicConfig(
    level=logging.INFO,
    format='{"ts":"%(asctime)s","lvl":"%(levelname)s","msg":"%(message)s","logger":"%(name)s"}',
)

def parse_args():
    p = argparse.ArgumentParser(description="Batch bootstrapper")
    p.add_argument("--start-schedule", action="store_true", help="APScheduler를 시작합니다.")
    p.add_argument("--run-now", type=str, help='즉시 실행 파라미터(JSON). 예: "{\"topic\":\"ai\",\"count\":2}"')
    return p.parse_args()

async def main():
    args = parse_args()

    if args.start_schedule:
        await start_scheduler()

    if args.run_now:
        try:
            params = json.loads(args.run_now)
        except json.JSONDecodeError:
            logging.error("run-now JSON 파싱 실패")
            sys.exit(2)
        res = await run_now(params)
        logging.info("run-now result=%s", res)

    if not args.start_schedule and not args.run_now:
        print("예시:")
        print("  python operators/execute_schedule.py --start-schedule")
        print("  python operators/execute_schedule.py --run-now '{\"topic\":\"news\",\"count\":2}'")
        print("  python -m operators.execute_schedule --run-now '{\"topic\":\"news\"}'")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
