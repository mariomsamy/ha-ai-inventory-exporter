ARG BUILD_FROM
FROM $BUILD_FROM

RUN apk add --no-cache python3 py3-websocket-client py3-requests

COPY rootfs /

RUN chmod a+x /usr/bin/run.sh /usr/bin/export_inventory.py

CMD ["/usr/bin/run.sh"]
