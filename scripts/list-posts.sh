#!/bin/bash

# Script to list all scheduled posts

API_URL="http://localhost:8000/api/v1/scheduled"

echo "Scheduled Posts:"
echo "================"
curl -s "$API_URL" | jq .