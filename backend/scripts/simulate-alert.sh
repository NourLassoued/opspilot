#!/usr/bin/env bash
# Simule Alertmanager : envoie une alerte "firing" au backend OpsPilot.
# Usage : ./scripts/simulate-alert.sh [namespace] [nom_alerte]
set -euo pipefail
NS="${1:-jobradar}"
ALERT="${2:-JobRadarBackendDown}"
URL="${BACKEND_URL:-http://localhost:8090}"
TOKEN="${ALERTMANAGER_TOKEN:-change-me}"

curl -sS -X POST "$URL/api/alerts/alertmanager" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d @- <<JSON
{
  "status": "firing",
  "receiver": "opspilot",
  "alerts": [
    {
      "status": "firing",
      "labels": { "alertname": "$ALERT", "namespace": "$NS", "severity": "critical" },
      "annotations": { "summary": "Alerte simulée pour tester OpsPilot" },
      "startsAt": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    }
  ]
}
JSON
echo
