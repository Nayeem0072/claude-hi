# claude-hi

Sends `hi` to Claude every 5 hours 5 minutes to keep your subscription usage window rolling. When you hit the token limit, the window was already triggered recently — so you wait less.

---

## Configuration

Edit `.env` before running:

| Variable | Default | Description |
|---|---|---|
| `INTERVAL_MINUTES` | `305` | How often to ping Claude (5h 5m = 305) |
| `START_TIME` | *(required)* | First ping time of day (`HH:MM`, 24h). Waits if started before this time; pings immediately if started after. |

```dotenv
INTERVAL_MINUTES=305
START_TIME=09:00
```

---

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env   # then set START_TIME
```

---

## Run

**Foreground:**

```bash
python3 hi.py
```

**Background** (survives closing the terminal):

```bash
nohup python3 hi.py >> hi.log 2>&1 &
echo $! > hi.pid
```

**Stop background process:**

```bash
kill $(cat hi.pid)
```

---

## Output

```
============================================================
  claude-hi  |  interval: 5h 05m  |  start: 09:00
  started:   2026-06-09 20:17:00
  log file:  /path/to/claude-hi/hi.log
============================================================
2026-06-09 20:17:04  INFO     Past 09:00 — pinging now.
2026-06-09 20:17:09  INFO     Sent 'hi' to Claude successfully.
  Next ping in: 5h 04m 55s   [Ctrl+C to stop]
```

Logs are written to `hi.log` (1 MB cap, 3 rotating backups).
