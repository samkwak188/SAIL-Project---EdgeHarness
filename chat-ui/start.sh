#!/usr/bin/env bash
# Start the SAIL chat UI: backend (:8800) + frontend (:5173), then open Chrome.
set -e
cd "$(dirname "$0")"

source ../sail-platform/.venv/bin/activate
set -a; source ../sail-platform/.env; set +a

trap 'kill 0' EXIT INT TERM

(cd server && uvicorn app:app --port 8800) &
(cd web && npm run dev) &

# wait for vite, then open the browser
for _ in $(seq 1 30); do
  curl -s -o /dev/null http://localhost:5173 && break
  sleep 0.5
done
open -a "Google Chrome" http://localhost:5173 2>/dev/null || open http://localhost:5173

wait
