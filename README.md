# WSDOT Traffic — Home Assistant Integration

[![HACS](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://hacs.xyz)
![HA Version](https://img.shields.io/badge/HA-2023.1%2B-blue)

A full-featured Home Assistant integration for **WSDOT** (Washington State Department of Transportation) live traffic data. Features real-time travel times, mountain pass conditions, highway camera feeds, and an interactive Lovelace map panel.

---

## Features

| Feature | Details |
|---|---|
| 🚗 Travel Time Sensors | Current & average travel time for all statewide routes |
| ⛰️ Mountain Pass Sensors | Road condition, temperature, restrictions for all WA passes |
| 📷 Highway Cameras | Live JPEG snapshot entities for all active highway cameras |
| 🚦 Congestion Alerts | Binary sensors that trigger when routes exceed 125% of average |
| ⚠️ Travel Advisories | Binary sensors for active pass travel advisories |
| 🗺️ Lovelace Map Panel | Interactive Leaflet map with camera pins, route overlays, and pass markers |

## Installation

### Via HACS (Recommended)

1. Go to **HACS → Integrations → ⋮ → Custom Repositories**
2. Add this repo URL with category **Integration**
3. Install **WSDOT Traffic**
4. Restart Home Assistant

### Manual

1. Copy the `custom_components/wsdot` folder to your HA's `config/custom_components/` directory
2. Copy `www/wsdot-panel.js` to your HA's `config/www/` directory
3. Restart Home Assistant

## Configuration

1. Go to **Settings → Devices & Services → Add Integration**
2. Search for **WSDOT Traffic**
3. Enter your WSDOT API key (get one free at [data.wsdot.wa.gov](https://wsdot.wa.gov/traffic/api/))
4. Click **Submit**

The integration will create entities for all statewide routes, passes, and cameras automatically.

## Lovelace Panel Setup

Add the panel resource and panel configuration to your `configuration.yaml`:

```yaml
# In configuration.yaml
lovelace:
  mode: storage  # or yaml
  resources:
    - url: /local/wsdot-panel.js
      type: module

  # If using yaml mode, add to panels:
panel_custom:
  - name: wsdot
    sidebar_title: WSDOT Traffic
    sidebar_icon: mdi:traffic-cone
    url_path: wsdot
    module_url: /local/wsdot-panel.js
    embed_iframe: false
    trust_external_panels: true
```

Then restart Home Assistant and find **WSDOT Traffic** in the sidebar.

## Entity Naming

| Entity ID Pattern | Description |
|---|---|
| `sensor.wsdot_tt_{id}_current_travel_time` | Current route travel time (min) |
| `sensor.wsdot_tt_{id}_average_travel_time` | Typical route travel time (min) |
| `sensor.wsdot_pass_{id}_road_condition` | Pass road condition text |
| `sensor.wsdot_pass_{id}_temperature` | Pass temperature (°F) |
| `camera.wsdot_camera_{id}` | Live highway camera snapshot |
| `binary_sensor.wsdot_tt_{id}_congestion` | Route congestion alert |
| `binary_sensor.wsdot_pass_{id}_advisory` | Pass travel advisory alert |

## Update Interval

Default: **60 seconds** (configurable 30s–3600s via Options).

Note: WSDOT typically updates travel time data every 1–5 minutes. Setting the interval below 60s will not yield fresher data.

## Automations Example

```yaml
automation:
  - alias: "Alert: Snoqualmie Pass Advisory"
    trigger:
      - platform: state
        entity_id: binary_sensor.wsdot_pass_11_advisory
        to: "on"
    action:
      - service: notify.mobile_app_your_phone
        data:
          message: "⚠️ Snoqualmie Pass travel advisory is now active!"
```

## API Key

Get a free API key at: **https://wsdot.wa.gov/traffic/api/**

## Credits

Data provided by the **Washington State Department of Transportation (WSDOT)**.
