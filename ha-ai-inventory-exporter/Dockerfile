FROM ghcr.io/home-assistant/base:latest

ARG BUILD_VERSION
ARG BUILD_ARCH

LABEL \
    io.hass.name="AI Inventory Exporter" \
    io.hass.description="Exports a full Home Assistant inventory JSON for AI-assisted automations and dashboards." \
    io.hass.version="${BUILD_VERSION}" \
    io.hass.type="addon" \
    org.opencontainers.image.title="AI Inventory Exporter" \
    org.opencontainers.image.description="Home Assistant add-on that exports an AI-ready full inventory JSON." \
    org.opencontainers.image.source="https://github.com/mariomsamy/ha-ai-inventory-exporter"

RUN apk add --no-cache python3 py3-websocket-client py3-requests

COPY rootfs /

RUN chmod a+x /usr/bin/run.sh /usr/bin/export_inventory.py

CMD ["/usr/bin/run.sh"]
