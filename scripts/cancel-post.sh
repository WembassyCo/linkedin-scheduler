#!/bin/bash

# Script to cancel a scheduled post

API_URL="http://localhost:8000/api/v1/scheduled"
POST_ID="$1"

if [ -z "$POST_ID" ]; then
    echo "Usage: $0 <post_id>"
    exit 1
fi

echo "Cancelling post $POST_ID..."
curl -X DELETE "$API_URL/$POST_ID" | jq .