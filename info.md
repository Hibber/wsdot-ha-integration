# WSDOT Traffic Integration for Home Assistant

Real-time Washington State DOT data: travel times, mountain pass conditions, highway cameras, and an interactive Leaflet map panel — all in Home Assistant.

## Features
- 🚗 Live travel times for all statewide routes (current vs. average)
- ⛰️ Mountain pass conditions, temperature, and restrictions
- 📷 Highway camera snapshots as HA camera entities
- 🚦 Congestion alert binary sensors
- ⚠️ Pass travel advisory binary sensors
- 🗺️ Beautiful interactive Lovelace map with camera pins and route overlays

## Installation

[![Install via HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=yourusername&repository=wsdot-ha-integration&category=integration)

Or install manually — see [README.md](README.md) for full instructions.

## Requirements

- Home Assistant 2023.1+
- A free WSDOT Traffic API key from [wsdot.wa.gov](https://wsdot.wa.gov/traffic/api/)
