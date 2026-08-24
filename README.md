# Mario's Home Assistant AI Add-ons

This repository contains Home Assistant add-ons built to make AI-assisted home automation and dashboard work easier.

## Available Add-ons

### AI Inventory Exporter

Automatically exports a complete, AI-ready Home Assistant inventory JSON.

Add-on folder:

```text
ha-ai-inventory-exporter
```

Main features:

- Generates `home_assistant_full_inventory.json`.
- Runs automatically on a schedule.
- Uses Home Assistant's internal add-on API token.
- Does not require a user-created long-lived access token.
- Provides a sidebar UI called **AI Inventory**.
- Lets you generate, download, and open the JSON from Home Assistant.
- Exports entities, devices, areas, services, states, Lovelace panels, config entries, and enriched indexes.

## Add This Repository To Home Assistant

1. Open Home Assistant.
2. Go to `Settings -> Add-ons -> Add-on Store`.
3. Click the three-dot menu.
4. Click `Repositories`.
5. Add:

   ```text
   https://github.com/mariomsamy/ha-ai-inventory-exporter
   ```

6. Reload the Add-on Store if needed.
7. Install **AI Inventory Exporter**.

## How To Use AI Inventory Exporter

After installing and starting the add-on:

1. Enable **Show in sidebar**.
2. Open **AI Inventory** from the sidebar.
3. Click **Generate now**.
4. Use the generated JSON at:

   ```text
   /local/ai/home_assistant_full_inventory.json
   ```

Full documentation:

```text
ha-ai-inventory-exporter/README.md
```

## Repository Metadata

Home Assistant reads this file:

```text
repository.yaml
```

It tells Home Assistant that this GitHub repository is an add-on repository.
