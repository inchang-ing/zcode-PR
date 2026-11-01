#!/usr/bin/env bash
# Keep polling for the whole life of one job instead of trusting the cron.
#
# Measured on 2026-11-01: the `*/5` schedule registered 34 slots in 166 minutes
# and fired once (2.9%). GitHub documents drift under load, not a 97% dropout,
# so the reason is unknown. Rather than keep guessing, invert the assumption:
# treat a trigger as rare and valuable, and spend each one on a long shift.
#
# A GitHub-hosted job may run for up to six hours. Inside that window the loop
# below polls every INTERVAL_SEC, so a single trigger buys hours of coverage. A
# trigger every few hours is then more than enough, which is exactly the
# behaviour observed.
#
# Cadence is capped by the token, not by taste: an installation token gets 1000
# requests per hour per repository, and one poll costs one request per pooled
# repo (88). At 360s that is 10 polls/hour x 88 = 880, leaving room for the
# occasional comment write. Shortening the interval without raising the budget
# will start returning 403s partway through a shift.
set -u

interval="${INTERVAL_SEC:-360}"
duration_min="${DURATION_MIN:-340}"
max_rounds="${MAX_ROUNDS:-0}"
deadline=$(( $(date +%s) + duration_min * 60 ))

poll_once() {
    timeout 240 python tools/poll_fresh.py "$@"
    return $?
}

round=0
while [ "$(date +%s)" -lt "$deadline" ]; do
    if [ "$max_rounds" -gt 0 ] && [ "$round" -ge "$max_rounds" ]; then
        break
    fi
    round=$((round + 1))
    echo "--- round $round at $(date -u +%Y-%m-%dT%H:%M:%SZ) ---"
    # A transient API error must not end a six-hour shift; the next round is
    # six minutes away and the lookback window covers whatever was missed.
    if ! poll_once "$@"; then
        echo "round $round failed, continuing"
    fi
    if [ "$max_rounds" -gt 0 ] && [ "$round" -ge "$max_rounds" ]; then
        break
    fi
    sleep "$interval"
done

echo "shift finished after $round round(s) at $(date -u +%Y-%m-%dT%H:%M:%SZ)"
