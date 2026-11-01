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
# repo (88). At 900s that is 4 polls/hour x 88 = 352, a third of the budget, so
# there is headroom for comment writes and the switch lookup. At 360s the same
# arithmetic left 120 requests for everything else, which was tighter than it
# needed to be -- 15 minutes is enough for a lane that only reports.
set -u

interval="${INTERVAL_SEC:-900}"
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
    # one interval away and the lookback window covers whatever was missed.
    poll_once "$@"
    rc=$?
    if [ "$rc" = "42" ]; then
        # 42 is the poller's "switch is off" code, not a failure: stop now
        # rather than at the end of the shift, so turning the lane off takes
        # effect within one interval instead of within six hours.
        echo "pipeline switch is off, ending shift early"
        break
    elif [ "$rc" != "0" ]; then
        echo "round $round failed ($rc), continuing"
    fi
    if [ "$max_rounds" -gt 0 ] && [ "$round" -ge "$max_rounds" ]; then
        break
    fi
    # Sleep only until the deadline, never past it: sleeping a full interval
    # after the final round kept a short shift alive well beyond its length.
    remaining=$(( deadline - $(date +%s) ))
    if [ "$remaining" -le 0 ]; then
        break
    fi
    if [ "$remaining" -lt "$interval" ]; then
        sleep "$remaining"
    else
        sleep "$interval"
    fi
done

echo "shift finished after $round round(s) at $(date -u +%Y-%m-%dT%H:%M:%SZ)"
