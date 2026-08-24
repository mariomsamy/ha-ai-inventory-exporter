# AI Inventory Exporter

AI Inventory Exporter is a Home Assistant add-on that automatically generates a complete, AI-ready inventory of your Home Assistant setup.

It is designed for workflows where an AI assistant needs to understand your entities, rooms, devices, automations, services, sensors, and dashboards before creating automations or improving Lovelace dashboards.

## Main Features

- Exports `home_assistant_full_inventory.json` automatically.
- Runs inside Home Assistant OS as an add-on.
- Does not require a user-created long-lived access token.
- Uses Home Assistant's internal add-on API token.
- Generates an enriched entity inventory with area, device, platform, state, and attribute context.
- Indexes entities by area, domain, platform, MQTT, ESPHome, and device.
- Includes a Home Assistant sidebar page called **AI Inventory**.
- Provides buttons to generate, preview, and download JSON inside the sidebar page.
- Runs on a schedule, every 60 minutes by default.
- Can also run once and stop.
- Writes the file atomically to avoid half-written JSON.
- Works well for AI-assisted automation creation, dashboard cleanup, room mapping, device audits, and troubleshooting.

## What It Exports

The generated JSON includes:

- Home Assistant configuration metadata
- Runtime entity states
- Service list
- Lovelace panels
- Device registry
- Entity registry
- Area registry
- Floor registry
- Label registry
- Config entries, when available
- Exposed entity information, when available
- Enriched entity index
- Enriched device index
- Entities grouped by area
- Entities grouped by domain
- Entities grouped by platform
- MQTT entity index
- ESPHome entity index
- High-level statistics

## Default Output

By default, the add-on writes:

```text
/config/www/ai/home_assistant_full_inventory.json
```

Home Assistant exposes files under `/config/www` through `/local`, so the JSON is available at:

```text
/local/ai/home_assistant_full_inventory.json
```

For example:

```text
http://YOUR_HOME_ASSISTANT_HOST:8123/local/ai/home_assistant_full_inventory.json
```

## Sidebar UI

After installation, enable **Show in sidebar** for the add-on.

The sidebar page is named:

```text
AI Inventory
```

From the sidebar page you can:

- See when the inventory was last generated.
- See the output path.
- See the public JSON URL.
- View inventory statistics.
- Generate a fresh export immediately without leaving the page.
- Preview the JSON inside the page.
- Download the JSON file without redirecting away from the add-on.

## Install From This GitHub Repository

1. Open Home Assistant.
2. Go to `Settings -> Add-ons -> Add-on Store`.
3. Click the three-dot menu in the top right.
4. Click `Repositories`.
5. Add this repository URL:

   ```text
   https://github.com/mariomsamy/ha-ai-inventory-exporter
   ```

6. Close the repositories dialog.
7. Reload the Add-on Store if Home Assistant does not refresh automatically.
8. Find `AI Inventory Exporter`.
9. Click **Install**.
10. After installation, enable `Start on boot`, `Watchdog`, and `Show in sidebar`.
11. Click **Start**.
12. Open **AI Inventory** from the sidebar.
13. Click **Generate now** or wait for the scheduled export.

## Manual Local Add-on Installation

If you do not want to use a GitHub add-on repository:

1. Copy the add-on folder into HAOS:

   ```text
   /addons/ha-ai-inventory-exporter
   ```

2. Open Home Assistant.
3. Go to `Settings -> Add-ons -> Add-on Store`.
4. Click the three-dot menu.
5. Click `Reload`.
6. Open **Local add-ons**.
7. Install **AI Inventory Exporter**.
8. Start the add-on.

## Configuration Options

Default options:

```yaml
output_path: /config/www/ai/home_assistant_full_inventory.json
interval_minutes: 60
run_once: false
```

### `output_path`

Where the JSON file should be written inside Home Assistant.

Recommended:

```text
/config/www/ai/home_assistant_full_inventory.json
```

Use a private `/config/...` path instead if you do not want the JSON exposed through `/local`.

### `interval_minutes`

How often the add-on regenerates the inventory.

Default: `60`

Minimum: `5`

Maximum: `1440`

### `run_once`

If set to `true`, the add-on generates the file once and then exits.

Use this if you prefer manual exports only.

## How To Use With AI

1. Install and start the add-on.
2. Open **AI Inventory** in the sidebar.
3. Click **Generate now**.
4. Click **Show full JSON here** to inspect it in the sidebar, or download the file.
5. Share the JSON URL or file with your AI tool:

   ```text
   /local/ai/home_assistant_full_inventory.json
   ```

6. Ask the AI to inspect the inventory before creating automations or dashboard changes.

Example prompts:

```text
Learn from this Home Assistant inventory and suggest safe automations.
```

```text
Use this inventory to improve my room dashboard without using dead entities.
```

```text
Find duplicate or risky automations based on this inventory.
```

```text
Create guest-aware automations using presence sensors, media state, and people.
```

## Suggested AI Workflow

For best results, ask the AI to follow this order:

1. Read the inventory.
2. Identify rooms and areas.
3. Identify available sensors.
4. Identify controllable entities.
5. Check for existing automations.
6. Avoid duplicates.
7. Prefer notifications for safety-critical events.
8. Make guest-aware logic for away automations.
9. Validate all referenced entities before saving.
10. Keep a backup of dashboards or automations before editing.

## Security Notes

The add-on does not store or ask for your personal Home Assistant long-lived token.

It uses:

```text
SUPERVISOR_TOKEN
```

This token is provided by Home Assistant to add-ons when `homeassistant_api` is enabled.

## Add-on Build Lessons

This add-on follows the HAOS patterns that matter most for reliable future add-ons:

- Use an explicit base image in `Dockerfile`, such as `ghcr.io/home-assistant/base:latest`.
- Do not depend on Supervisor injecting `BUILD_FROM`.
- Use `homeassistant_api: true` and the provided `SUPERVISOR_TOKEN` instead of asking users for long-lived tokens.
- Mount Home Assistant config explicitly with object syntax:

  ```yaml
  map:
    - type: homeassistant_config
      read_only: false
      path: /config
  ```

- Write public files under `/config/www/...`; Home Assistant serves them as `/local/...`.
- Keep the sidebar page self-contained through ingress APIs so actions do not redirect users away from the add-on.
- Return machine-readable JSON from action endpoints and let the page update status, preview, and errors in place.

The token is used only inside the add-on container and is never written to the exported JSON.

Important: if the output path is inside `/config/www`, the JSON is reachable through `/local`. That is useful for AI tools, but it may expose details about your home setup to anyone who can access your Home Assistant instance.

If you want a private export, change `output_path` to another `/config/...` location that is not under `/config/www`.

## Troubleshooting

### The add-on does not appear in the Add-on Store

Check that the repository URL was added:

```text
https://github.com/mariomsamy/ha-ai-inventory-exporter
```

Then reload the Add-on Store.

### The sidebar item does not appear

Open the add-on page and enable `Show in sidebar`.

Then refresh Home Assistant.

### The JSON file is not created

Open the add-on logs and check for errors.

Also confirm the output path is writable:

```text
/config/www/ai/home_assistant_full_inventory.json
```

### The public JSON URL returns 404

Generate the file first from the sidebar.

Then open:

```text
/local/ai/home_assistant_full_inventory.json
```

### The export is old

Click **Generate now** from the sidebar, or reduce:

```yaml
interval_minutes: 60
```

### The add-on starts and exits

Check whether `run_once` is enabled:

```yaml
run_once: true
```

Set it to `false` if you want continuous scheduled exports.

## Sharing This Add-on

Share this repository URL:

```text
https://github.com/mariomsamy/ha-ai-inventory-exporter
```

Other users can add it to Home Assistant through:

```text
Settings -> Add-ons -> Add-on Store -> three-dot menu -> Repositories
```

## Repository Structure

```text
repository.yaml
ha-ai-inventory-exporter/
  config.yaml
  Dockerfile
  README.md
  DOCS.md
  rootfs/
    usr/bin/
      run.sh
      export_inventory.py
      inventory_web.py
  translations/
    en.yaml
```

## License

No license has been selected yet. Add a license before distributing this add-on publicly beyond personal use.
