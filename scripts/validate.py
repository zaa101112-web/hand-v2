"""Capture actual test runs, including intentional Red stages, as evidence."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--label", required=True)
    parser.add_argument("--expect-failure", action="store_true")
    parser.add_argument("targets", nargs="*")
    args = parser.parse_args()
    report_dir = ROOT / "docs/validation/tdd"
    report_dir.mkdir(parents=True, exist_ok=True)
    xml = report_dir / f"{args.label}.xml"
    cmd = [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", f"--junitxml={xml}", *(args.targets or ["tests"])]
    env = dict(os.environ, QT_QPA_PLATFORM="offscreen", PYTHONIOENCODING="utf-8")
    start = time.monotonic()
    run = subprocess.run(cmd, cwd=ROOT, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace")
    output = run.stdout + run.stderr
    (report_dir / f"{args.label}.txt").write_text(output, encoding="utf-8")
    record = {"label": args.label, "at_utc": datetime.now(timezone.utc).isoformat(), "duration_seconds": round(time.monotonic()-start, 3),
              "exit_code": run.returncode, "expected_failure": args.expect_failure, "targets": args.targets or ["tests"]}
    with (report_dir / "runs.jsonl").open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(record, ensure_ascii=False) + "\n")
    print(output)
    return 0 if (run.returncode != 0 if args.expect_failure else run.returncode == 0) else 1

if __name__ == "__main__":
    raise SystemExit(main())
