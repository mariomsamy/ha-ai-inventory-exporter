#!/usr/bin/env python3

import argparse
import json
import os
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import requests
import websocket


CORE_API = "http://supervisor/core/api"
CORE_WS = "ws://supervisor/core/websocket"


def resolve_output_path(path: str) -> Path:
    if path.startswith("/homeassistant/") and not Path("/homeassistant").is_dir():
        if Path("/config").is_dir():
            return Path("/config") / path.removeprefix("/homeassistant/")
    return Path(path)


def get_token() -> str:
    token = os.environ.get("SUPERVISOR_TOKEN")
    if not token:
        raise RuntimeError("SUPERVISOR_TOKEN is missing")
    return token


def receive_json(ws):
    return json.loads(ws.recv())


def connect_ws(token: str):
    ws = websocket.create_connection(
        CORE_WS,
        timeout=30,
    )

    msg = receive_json(ws)
    if msg.get("type") == "auth_required":
        ws.send(json.dumps({"type": "auth", "access_token": token}))
        msg = receive_json(ws)

    if msg.get("type") != "auth_ok":
        raise RuntimeError(f"WebSocket authentication failed: {msg}")

    return ws


message_id = 1


def call_ws(ws, command_type, **kwargs):
    global message_id
    current_id = message_id
    message_id += 1

    ws.send(json.dumps({"id": current_id, "type": command_type, **kwargs}))

    while True:
        response = receive_json(ws)
        if response.get("id") != current_id:
            continue

        if not response.get("success", False):
            raise RuntimeError(response.get("error", response))

        return response.get("result")


def safe_call(ws, command_type, **kwargs):
    try:
        return {
            "success": True,
            "data": call_ws(ws, command_type, **kwargs),
        }
    except Exception as exc:
        return {
            "success": False,
            "error": str(exc),
            "data": None,
        }


def fetch_rest(token: str, path: str):
    response = requests.get(
        f"{CORE_API}{path}",
        headers={"Authorization": f"Bearer {token}"},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def build_inventory(token: str):
    mode = "websocket"
    warning = None

    try:
        ws = connect_ws(token)
        try:
            config = safe_call(ws, "get_config")
            states = safe_call(ws, "get_states")
            services = safe_call(ws, "get_services")
            panels = safe_call(ws, "get_panels")

            registries = {
                "devices": safe_call(ws, "config/device_registry/list"),
                "entities": safe_call(ws, "config/entity_registry/list"),
                "areas": safe_call(ws, "config/area_registry/list"),
                "floors": safe_call(ws, "config/floor_registry/list"),
                "labels": safe_call(ws, "config/label_registry/list"),
            }

            system = {
                "config_entries": safe_call(ws, "config_entries/get"),
                "entity_display_registry": safe_call(
                    ws,
                    "config/entity_registry/list_for_display",
                ),
                "exposed_entities": safe_call(ws, "homeassistant/expose_entity/list"),
            }
        finally:
            ws.close()
    except Exception as exc:
        mode = "rest_fallback"
        warning = f"WebSocket export failed, used REST fallback: {exc}"
        config = wrap_rest(lambda: fetch_rest(token, "/config"))
        states = wrap_rest(lambda: fetch_rest(token, "/states"))
        services = wrap_rest(lambda: fetch_rest(token, "/services"))
        panels = {
            "success": False,
            "error": "Not available in REST fallback",
            "data": None,
        }
        registries = {
            "devices": empty_result("Not available in REST fallback"),
            "entities": states_to_entity_registry(states.get("data") or []),
            "areas": empty_result("Not available in REST fallback"),
            "floors": empty_result("Not available in REST fallback"),
            "labels": empty_result("Not available in REST fallback"),
        }
        system = {
            "config_entries": empty_result("Not available in REST fallback"),
            "entity_display_registry": empty_result("Not available in REST fallback"),
            "exposed_entities": empty_result("Not available in REST fallback"),
        }

    inventory = {
        "metadata": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "exporter": "AI Inventory Exporter add-on",
            "exporter_version": "1.0.4",
            "core_api": CORE_API,
            "mode": mode,
            "warning": warning,
        },
        "home_assistant": {
            "config": config,
        },
        "registries": registries,
        "runtime": {
            "states": states,
            "services": services,
            "panels": panels,
        },
        "system": system,
        "indexes": {},
        "statistics": {},
    }

    enrich_inventory(inventory)
    return inventory


def wrap_rest(callback):
    try:
        return {"success": True, "data": callback()}
    except Exception as exc:
        return {"success": False, "error": str(exc), "data": None}


def empty_result(error):
    return {"success": False, "error": error, "data": []}


def states_to_entity_registry(states):
    entities = []
    for state in states:
        entity_id = state.get("entity_id")
        if not entity_id:
            continue
        attributes = state.get("attributes", {})
        entities.append(
            {
                "entity_id": entity_id,
                "name": attributes.get("friendly_name"),
                "original_name": attributes.get("friendly_name"),
                "platform": None,
                "device_id": None,
                "area_id": None,
                "disabled_by": None,
                "hidden_by": None,
                "entity_category": attributes.get("entity_category"),
                "device_class": attributes.get("device_class"),
                "original_device_class": attributes.get("device_class"),
                "unique_id": None,
                "config_entry_id": None,
            }
        )
    return {"success": True, "data": entities}


def enrich_inventory(inventory):
    states = inventory["runtime"]["states"].get("data") or []
    entities = inventory["registries"]["entities"].get("data") or []
    devices = inventory["registries"]["devices"].get("data") or []
    areas = inventory["registries"]["areas"].get("data") or []

    state_lookup = {item["entity_id"]: item for item in states if "entity_id" in item}
    device_lookup = {item["id"]: item for item in devices if "id" in item}
    area_lookup = {
        item["area_id"]: item
        for item in areas
        if "area_id" in item
    }

    enriched_entities = []
    for entity in entities:
        entity_id = entity.get("entity_id")
        state = state_lookup.get(entity_id, {})
        device_id = entity.get("device_id")
        device = device_lookup.get(device_id, {})
        area_id = entity.get("area_id") or device.get("area_id")
        area = area_lookup.get(area_id, {})
        domain = entity_id.split(".", 1)[0] if entity_id and "." in entity_id else None

        enriched_entities.append(
            {
                "entity_id": entity_id,
                "domain": domain,
                "name": entity.get("name"),
                "original_name": entity.get("original_name"),
                "platform": entity.get("platform"),
                "device_id": device_id,
                "device_name": device.get("name_by_user") or device.get("name"),
                "manufacturer": device.get("manufacturer"),
                "model": device.get("model"),
                "model_id": device.get("model_id"),
                "area_id": area_id,
                "area_name": area.get("name"),
                "state": state.get("state"),
                "attributes": state.get("attributes", {}),
                "last_changed": state.get("last_changed"),
                "last_updated": state.get("last_updated"),
                "disabled_by": entity.get("disabled_by"),
                "hidden_by": entity.get("hidden_by"),
                "entity_category": entity.get("entity_category"),
                "device_class": entity.get("device_class"),
                "original_device_class": entity.get("original_device_class"),
                "unique_id": entity.get("unique_id"),
                "config_entry_id": entity.get("config_entry_id"),
            }
        )

    inventory["indexes"]["entities_enriched"] = enriched_entities

    by_domain = defaultdict(list)
    by_platform = defaultdict(list)
    by_area = defaultdict(list)
    device_entities = defaultdict(list)

    for entity in enriched_entities:
        entity_id = entity.get("entity_id")
        if not entity_id:
            continue
        by_domain[entity.get("domain") or "unknown"].append(entity_id)
        by_platform[entity.get("platform") or "unknown"].append(entity_id)
        by_area[entity.get("area_name") or "unknown"].append(entity_id)
        if entity.get("device_id"):
            device_entities[entity["device_id"]].append(entity_id)

    inventory["indexes"]["entities_by_domain"] = dict(sorted(by_domain.items()))
    inventory["indexes"]["entities_by_platform"] = dict(sorted(by_platform.items()))
    inventory["indexes"]["entities_by_area"] = dict(sorted(by_area.items()))

    enriched_devices = []
    for device in devices:
        item = dict(device)
        device_id = item.get("id")
        area = area_lookup.get(item.get("area_id"), {})
        item["resolved_area_name"] = area.get("name")
        item["entities"] = device_entities.get(device_id, [])
        item["entity_count"] = len(item["entities"])
        enriched_devices.append(item)

    inventory["indexes"]["devices_enriched"] = enriched_devices

    mqtt_entities = [e for e in enriched_entities if e.get("platform") == "mqtt"]
    esphome_entities = [e for e in enriched_entities if e.get("platform") == "esphome"]

    inventory["indexes"]["mqtt"] = {
        "count": len(mqtt_entities),
        "entities": mqtt_entities,
    }
    inventory["indexes"]["esphome"] = {
        "count": len(esphome_entities),
        "entities": esphome_entities,
    }

    inventory["statistics"] = {
        "devices": len(devices),
        "entities": len(entities),
        "states": len(states),
        "areas": len(areas),
        "mqtt_entities": len(mqtt_entities),
        "esphome_entities": len(esphome_entities),
        "lights": len(by_domain.get("light", [])),
        "switches": len(by_domain.get("switch", [])),
        "fans": len(by_domain.get("fan", [])),
        "climate": len(by_domain.get("climate", [])),
        "media_players": len(by_domain.get("media_player", [])),
        "sensors": len(by_domain.get("sensor", [])),
        "binary_sensors": len(by_domain.get("binary_sensor", [])),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        default="/config/www/ai/home_assistant_full_inventory.json",
    )
    args = parser.parse_args()

    token = get_token()
    output = resolve_output_path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    status_path = output.parent / "export_status.json"

    try:
        inventory = build_inventory(token)
    except Exception as exc:
        status = {
            "ok": False,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "output": str(output),
            "error": str(exc),
        }
        status_path.write_text(json.dumps(status, indent=2), encoding="utf-8")
        raise

    tmp = output.with_suffix(output.suffix + ".tmp")
    tmp.write_text(
        json.dumps(inventory, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )
    tmp.replace(output)

    latest = output.parent / "latest.txt"
    latest.write_text(
        f"{datetime.now(timezone.utc).isoformat()} {output}\n",
        encoding="utf-8",
    )

    status = {
        "ok": True,
        "generated_at": inventory["metadata"]["generated_at"],
        "output": str(output),
        "mode": inventory["metadata"].get("mode"),
        "warning": inventory["metadata"].get("warning"),
        "statistics": inventory["statistics"],
    }
    status_path.write_text(json.dumps(status, indent=2), encoding="utf-8")

    print(
        json.dumps(
            {
                "output": str(output),
                "generated_at": inventory["metadata"]["generated_at"],
                "statistics": inventory["statistics"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
