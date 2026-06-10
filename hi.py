import os
import sys
import glob
import time
import signal
import logging
import subprocess
from datetime import datetime, timedelta
from logging.handlers import RotatingFileHandler

from dotenv import load_dotenv

# Use absolute path so load_dotenv works regardless of working directory
_HERE = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(_HERE, ".env"))

INTERVAL_SECONDS = int(os.getenv("INTERVAL_MINUTES", "305")) * 60
START_TIME = os.getenv("START_TIME", "").strip()
if not START_TIME:
    sys.exit("ERROR: START_TIME is required. Set it in .env (e.g. START_TIME=09:00)")

LOG_FILE = os.path.join(_HERE, "hi.log")
MAX_RETRIES = 3
RETRY_BASE_DELAY = 30


def _find_claude():
    # Find the latest installed Claude Code binary (works across version updates)
    pattern = os.path.expanduser(
        "~/Library/Application Support/Claude/claude-code/*/claude.app/Contents/MacOS/claude"
    )
    candidates = sorted(glob.glob(pattern))
    return candidates[-1] if candidates else "claude"


CLAUDE_CMD = [_find_claude(), "-p", "hi", "--no-session-persistence"]

shutdown = [False]


def setup_logging():
    fmt = "%(asctime)s  %(levelname)-7s  %(message)s"
    datefmt = "%Y-%m-%d %H:%M:%S"
    formatter = logging.Formatter(fmt, datefmt)

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setLevel(logging.INFO)
    stream_handler.setFormatter(formatter)

    file_handler = RotatingFileHandler(LOG_FILE, maxBytes=1_000_000, backupCount=3)
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    root.addHandler(stream_handler)
    root.addHandler(file_handler)


log = logging.getLogger(__name__)


def handle_signal(signum, frame):
    shutdown[0] = True


def start_target():
    h, m = map(int, START_TIME.split(":"))
    now = datetime.now()
    target = now.replace(hour=h, minute=m, second=0, microsecond=0)
    if target <= now:
        return None  # already past, ping immediately
    return target


def send_hi():
    try:
        result = subprocess.run(
            CLAUDE_CMD,
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode == 0:
            return True, None
        err = (result.stderr or result.stdout or "").strip()[:200]
        return False, err or f"exit code {result.returncode}"
    except subprocess.TimeoutExpired:
        return False, "timed out after 120s"
    except FileNotFoundError:
        return False, f"claude binary not found: {CLAUDE_CMD[0]}"
    except Exception as e:
        return False, str(e)


def send_with_retry():
    for attempt in range(1, MAX_RETRIES + 1):
        success, err = send_hi()
        if success:
            log.info("Sent 'hi' to Claude successfully.")
            return True
        delay = RETRY_BASE_DELAY * (2 ** (attempt - 1))
        if attempt < MAX_RETRIES:
            log.warning("Attempt %d failed: %s. Retrying in %ds...", attempt, err, delay)
            for _ in range(delay):
                if shutdown[0]:
                    return False
                time.sleep(1)
        else:
            log.error("All %d attempts failed. Last error: %s", MAX_RETRIES, err)
    return False


def countdown(target_time, label="Next ping in"):
    # Compare against wall-clock time so macOS sleep/wake doesn't stall the countdown
    while not shutdown[0]:
        remaining = int((target_time - datetime.now()).total_seconds())
        if remaining <= 0:
            break
        h, rem = divmod(remaining, 3600)
        m, s = divmod(rem, 60)
        sys.stdout.write(f"\r  {label}: {h}h {m:02d}m {s:02d}s   [Ctrl+C to stop]")
        sys.stdout.flush()
        time.sleep(1)
    sys.stdout.write("\r" + " " * 60 + "\r")
    sys.stdout.flush()


def main():
    setup_logging()
    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    interval_m = INTERVAL_SECONDS // 60
    interval_label = f"{interval_m // 60}h {interval_m % 60:02d}m"
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log.info("claude binary: %s", CLAUDE_CMD[0])
    print("=" * 60)
    print(f"  claude-hi  |  interval: {interval_label}  |  start: {START_TIME}")
    print(f"  started:   {now}")
    print(f"  log file:  {LOG_FILE}")
    print("=" * 60)

    target = start_target()
    if target is not None:
        delay = int((target - datetime.now()).total_seconds())
        h, rem = divmod(delay, 3600)
        m = rem // 60
        log.info("Before %s — waiting %dh %02dm for first ping.", START_TIME, h, m)
        countdown(target, label=f"First ping at {START_TIME} in")
        if shutdown[0]:
            log.info("Shutdown. Goodbye.")
            return
    else:
        log.info("Past %s — pinging now.", START_TIME)

    while not shutdown[0]:
        send_with_retry()
        if shutdown[0]:
            break
        next_ping = datetime.now() + timedelta(seconds=INTERVAL_SECONDS)
        countdown(next_ping)

    log.info("Shutdown. Goodbye.")


if __name__ == "__main__":
    main()
