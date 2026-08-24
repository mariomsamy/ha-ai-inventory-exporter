#!/usr/bin/with-contenv bashio

set -euo pipefail

OUTPUT_PATH="$(bashio::config 'output_path')"
INTERVAL_MINUTES="$(bashio::config 'interval_minutes')"
RUN_ONCE="$(bashio::config 'run_once')"

if [[ -z "${SUPERVISOR_TOKEN:-}" ]]; then
  bashio::log.fatal "SUPERVISOR_TOKEN is not available. Make sure homeassistant_api: true is set."
  exit 1
fi

bashio::log.info "AI Inventory Exporter started"
bashio::log.info "Output path: ${OUTPUT_PATH}"
bashio::log.info "Interval: ${INTERVAL_MINUTES} minutes"

/usr/bin/inventory_web.py --output "${OUTPUT_PATH}" --port 8099 &
WEB_PID="$!"
bashio::log.info "Ingress UI started on port 8099"

trap 'kill "${WEB_PID}" 2>/dev/null || true' EXIT

while true; do
  if /usr/bin/export_inventory.py --output "${OUTPUT_PATH}"; then
    bashio::log.info "Inventory export complete"
  else
    bashio::log.error "Inventory export failed"
  fi

  if [[ "${RUN_ONCE}" == "true" ]]; then
    bashio::log.info "run_once enabled; exiting"
    exit 0
  fi

  sleep "$((INTERVAL_MINUTES * 60))"
done
