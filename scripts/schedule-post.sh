#!/bin/bash

# Script to schedule a LinkedIn post

API_URL="http://localhost:8000/api/v1/schedule"

# Get arguments
CONTENT="${1:-Default post content}"
SCHEDULE_TIME="${2:-$(date -u -d '+1 hour' +%Y-%m-%dT%H:%M:%S)}"
VISIBILITY="${3:-PUBLIC}"
RECURRING="${4:-false}"
PATTERN="${5:-}"

curl -X POST "$API_URL" \
  -H "Content-Type: application/json" \
  -d "{
    \"content\": \"$CONTENT\",
    \"schedule_time\": \"$SCHEDULE_TIME\",
    \"visibility\": \"$VISIBILITY\",
    \"recurring\": $RECURRING,
    \"recurrence_pattern\": $([ -n \"$PATTERN\" ] && echo \"\"$PATTERN\"\" || echo null)
  }" | jq .