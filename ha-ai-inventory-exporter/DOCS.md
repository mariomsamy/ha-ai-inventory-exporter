# AI Inventory Exporter Documentation

This add-on creates `home_assistant_full_inventory.json` on a schedule so AI
tools can reason about the current Home Assistant setup without repeatedly
asking for a user token.

It also appears in the Home Assistant sidebar as **AI Inventory**. The sidebar
page shows the last export time, output location, high-level statistics, and
buttons to generate or download the JSON.

## Security Model

The add-on uses `homeassistant_api: true` and the `SUPERVISOR_TOKEN` made
available to Home Assistant add-ons. The token is used only from inside the
container to call Home Assistant Core through:

```text
http://supervisor/core/api
ws://supervisor/core/websocket
```

The token is never written to the exported JSON.

## Recommended Output Path

```text
/config/www/ai/home_assistant_full_inventory.json
```

This path lets tools fetch the latest export through:

```text
http://YOUR_HA_HOST:8123/local/ai/home_assistant_full_inventory.json
```

If you do not want the JSON available through `/local`, change `output_path` to
a private `/config/...` path.
