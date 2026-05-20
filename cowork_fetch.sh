#!/usr/bin/env bash
# cowork_fetch.sh
#
# Call this from the Cowork sandbox to fetch Yahoo Finance data.
# It triggers a GitHub Actions workflow (full internet on GitHub's runners)
# and polls until the JSON is committed back to data/ on main.
#
# Requirements:
#   - curl (pre-installed in most containers)
#   - GITHUB_PAT env var — a fine-grained PAT with:
#       Repository: yfinance-fetcher
#       Permissions: Actions (write), Contents (read)
#
# Usage:
#   ./cowork_fetch.sh defaults
#   ./cowork_fetch.sh AAPL 2020-01-01
#   ./cowork_fetch.sh ES=F 2022-01-01
#   ./cowork_fetch.sh BTC-USD 2020-01-01
#   ./cowork_fetch.sh SPY 2010-01-01 2023-12-31 1wk all
#
# Arguments:
#   $1  ticker   (required) — symbol or "defaults" for GEV+NVDA
#   $2  start    (optional) — YYYY-MM-DD
#   $3  end      (optional) — YYYY-MM-DD, default today
#   $4  interval (optional) — 1d | 1wk | 1mo | 1h | 15m …  default 1d
#   $5  fields   (optional) — close | all                    default close

set -euo pipefail

REPO="Glenn-So-JH/yfinance-fetcher"
API="https://api.github.com"
RAW="https://raw.githubusercontent.com/${REPO}/main/data"

TICKER="${1:-defaults}"
START="${2:-}"
END="${3:-}"
INTERVAL="${4:-1d}"
FIELDS="${5:-close}"

if [ -z "${GITHUB_PAT:-}" ]; then
  echo "ERROR: GITHUB_PAT is not set."
  echo "  export GITHUB_PAT=<your-fine-grained-pat>"
  exit 1
fi

AUTH="Authorization: Bearer $GITHUB_PAT"
ACCEPT="Accept: application/vnd.github+json"
WORKFLOW_ID="fetch.yml"

# ── 1. Trigger the workflow ────────────────────────────────────────────────────
echo "▶ Triggering workflow for ticker=$TICKER ..."

PAYLOAD=$(python3 -c "
import json, sys
inp = {
    'ticker':   '$TICKER',
    'start':    '$START',
    'end':      '$END',
    'interval': '$INTERVAL',
    'fields':   '$FIELDS',
}
print(json.dumps({'ref': 'main', 'inputs': inp}))
")

TRIGGER_STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
  -X POST \
  -H "$AUTH" -H "$ACCEPT" \
  -d "$PAYLOAD" \
  "$API/repos/$REPO/actions/workflows/$WORKFLOW_ID/dispatches")

if [ "$TRIGGER_STATUS" != "204" ]; then
  echo "ERROR: Failed to trigger workflow (HTTP $TRIGGER_STATUS)."
  echo "  Check that GITHUB_PAT has Actions:write permission on $REPO."
  exit 1
fi

echo "  Workflow triggered (HTTP 204). Waiting for it to start..."
sleep 5

# ── 2. Get the run ID of the most-recent run ──────────────────────────────────
RUN_ID=$(curl -s \
  -H "$AUTH" -H "$ACCEPT" \
  "$API/repos/$REPO/actions/workflows/$WORKFLOW_ID/runs?per_page=1" \
  | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['workflow_runs'][0]['id'])")

echo "  Run ID: $RUN_ID"
echo "  Track at: https://github.com/$REPO/actions/runs/$RUN_ID"

# ── 3. Poll until the run completes ──────────────────────────────────────────
echo "▶ Polling for completion (checks every 10 s) ..."
ELAPSED=0
MAX_WAIT=300   # 5 minutes

while true; do
  STATUS=$(curl -s \
    -H "$AUTH" -H "$ACCEPT" \
    "$API/repos/$REPO/actions/runs/$RUN_ID" \
    | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['status'], d['conclusion'] or '')")

  WSTATUS=$(echo "$STATUS" | awk '{print $1}')
  CONCLUSION=$(echo "$STATUS" | awk '{print $2}')

  if [ "$WSTATUS" = "completed" ]; then
    if [ "$CONCLUSION" = "success" ]; then
      echo "  ✓ Workflow succeeded."
      break
    else
      echo "  ✗ Workflow finished with conclusion: $CONCLUSION"
      echo "    See: https://github.com/$REPO/actions/runs/$RUN_ID"
      exit 1
    fi
  fi

  echo "  ... status=$WSTATUS (${ELAPSED}s elapsed)"
  sleep 10
  ELAPSED=$((ELAPSED + 10))

  if [ "$ELAPSED" -ge "$MAX_WAIT" ]; then
    echo "  Timeout after ${MAX_WAIT}s."
    exit 1
  fi
done

# ── 4. Fetch the result from raw.githubusercontent.com ───────────────────────
safe_name() {
  echo "$1" | tr '=^' '__' | tr '[:upper:]' '[:lower:]'
}

echo "▶ Downloading result ..."

if [ "$TICKER" = "defaults" ]; then
  for T in gev nvda; do
    URL="$RAW/${T}_prices.json"
    curl -fsSL "$URL" -o "${T}_prices.json"
    echo "  Saved ${T}_prices.json ($(wc -c < "${T}_prices.json") bytes)"
  done
else
  SAFE=$(safe_name "$TICKER")
  URL="$RAW/${SAFE}_prices.json"
  OUTFILE="${SAFE}_prices.json"
  curl -fsSL "$URL" -o "$OUTFILE"
  echo "  Saved $OUTFILE ($(wc -c < "$OUTFILE") bytes)"
fi

echo "Done."
