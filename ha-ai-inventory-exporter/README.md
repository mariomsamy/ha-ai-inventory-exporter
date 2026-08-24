# AI Inventory Exporter

Exports a complete Home Assistant inventory JSON for AI-assisted automations,
dashboard generation, and system review.

The add-on does not need a user-provided long-lived token. It runs inside HAOS
and uses Home Assistant's internal add-on API token.

Default output:

```text
/config/www/ai/home_assistant_full_inventory.json
```

The add-on also exposes an **AI Inventory** sidebar page through Home Assistant
Ingress. From there you can see export status, generate now, download the JSON,
or open the public JSON path.

After the add-on runs, the file is available through Home Assistant's local
static path:

```text
/local/ai/home_assistant_full_inventory.json
```

## Installation

1. Copy this folder to your HAOS local add-ons folder:

   ```text
   /addons/ai_inventory_exporter
   ```

2. In Home Assistant, go to:

   ```text
   Settings -> Add-ons -> Add-on Store -> three dots -> Reload
   ```

3. Open **Local add-ons**, install **AI Inventory Exporter**, and start it.

4. Leave **Start on boot** enabled.

5. Open **AI Inventory** from the sidebar.

## Options

```yaml
output_path: /config/www/ai/home_assistant_full_inventory.json
interval_minutes: 60
run_once: false
```

Set `run_once: true` if you only want one export per manual start.

## Sharing

For another HAOS install, share either:

- this whole `ha-ai-inventory-exporter` folder, or
- `ha-ai-inventory-exporter.zip`

To publish it properly, put this folder inside a GitHub repository with a
top-level `repository.yaml` file and add that repository URL in:

```text
Settings -> Add-ons -> Add-on Store -> three dots -> Repositories
```

Minimal `repository.yaml`:

```yaml
name: Mario's Home Assistant Add-ons
url: https://github.com/mariomsamy/ha-ai-inventory-exporter
maintainer: Mario
```

## What It Exports

- Home Assistant config
- Runtime states
- Service list
- Lovelace panels
- Device registry
- Entity registry
- Area, floor, and label registries
- Config entries when available
- Enriched indexes by area, domain, platform, MQTT, ESPHome, and device
