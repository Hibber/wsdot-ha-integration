class WsdotPanel extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._hass = null;
    this._map = null;
    this._markers = [];
  }

  set hass(hass) {
    this._hass = hass;
    if (this._map) this._updateMarkers();
  }

  connectedCallback() {
    this.shadowRoot.innerHTML = `
      <style>
        :host {
          display: block;
          position: absolute;
          inset: 0;
          background: #0f1117;
          font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        }
        #map {
          width: 100%;
          height: 100%;
          background: #1a2035;
          z-index: 1;
        }
        .legend {
          position: absolute;
          top: 16px;
          left: 16px;
          z-index: 1000;
          background: rgba(26, 29, 39, 0.95);
          backdrop-filter: blur(10px);
          padding: 16px;
          border-radius: 12px;
          border: 1px solid rgba(255, 255, 255, 0.1);
          color: #e2e8f0;
          font-size: 13px;
          box-shadow: 0 4px 20px rgba(0,0,0,0.5);
        }
        .legend h3 {
          margin: 0 0 12px 0;
          font-size: 15px;
          color: #fff;
        }
        .legend-item {
          display: flex;
          align-items: center;
          gap: 10px;
          margin-bottom: 8px;
        }
        .legend-item:last-child { margin-bottom: 0; }
        .dot {
          width: 20px;
          height: 20px;
          border-radius: 50%;
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 11px;
          border: 2px solid rgba(255,255,255,0.8);
        }
        /* Leaflet popup dark theme overrides */
        .leaflet-popup-content-wrapper {
          background: #1a1d27 !important;
          color: #e2e8f0 !important;
          border-radius: 12px !important;
          border: 1px solid rgba(255,255,255,0.1);
          box-shadow: 0 10px 30px rgba(0,0,0,0.8) !important;
        }
        .leaflet-popup-tip { background: #1a1d27 !important; }
        .popup-content { text-align: center; min-width: 200px; }
        .popup-title { font-weight: bold; margin-bottom: 8px; color: #fff; font-size: 14px; }
        .popup-img { width: 100%; max-width: 320px; border-radius: 6px; margin-top: 8px; display: block; background: #000; min-height: 150px; }
        .popup-stat { padding: 4px 0; border-top: 1px solid rgba(255,255,255,0.05); }
      </style>
      <div id="map"></div>
      <div class="legend">
        <h3>🚦 WSDOT Live Map</h3>
        <div class="legend-item"><div class="dot" style="background:#3b82f6;">📷</div> Highway Cameras</div>
        <div class="legend-item"><div class="dot" style="background:#10b981;">🚗</div> Travel Times (Normal)</div>
        <div class="legend-item"><div class="dot" style="background:#f59e0b;">🚗</div> Travel Times (Slow)</div>
        <div class="legend-item"><div class="dot" style="background:#ef4444;">🚗</div> Travel Times (Heavy)</div>
        <div class="legend-item"><div class="dot" style="background:#8b5cf6;">⛰️</div> Mountain Passes</div>
      </div>
    `;
    this._loadLeaflet();
  }

  _loadLeaflet() {
    if (!document.querySelector("#leaflet-css")) {
      const link = document.createElement("link");
      link.id = "leaflet-css";
      link.rel = "stylesheet";
      link.href = "https://unpkg.com/leaflet@1.9.4/dist/leaflet.css";
      document.head.appendChild(link);
    }
    if (!window.L) {
      const script = document.createElement("script");
      script.src = "https://unpkg.com/leaflet@1.9.4/dist/leaflet.js";
      script.onload = () => this._initMap();
      document.head.appendChild(script);
    } else {
      this._initMap();
    }
  }

  _initMap() {
    const mapEl = this.shadowRoot.querySelector("#map");
    if (!mapEl || this._map) return;

    // Centered on Olympia/Tacoma corridor
    this._map = L.map(mapEl).setView([47.037, -122.900], 10);
    
    L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", {
      attribution: '&copy; OSM &copy; CARTO | WSDOT',
      maxZoom: 19
    }).addTo(this._map);

    this._updateMarkers();
    
    // Force map to recalculate bounds after HA finishes animations
    setTimeout(() => this._map.invalidateSize(), 100);
    setTimeout(() => this._map.invalidateSize(), 500);
    window.addEventListener("resize", () => {
      if (this._map) this._map.invalidateSize();
    });
  }

  _createIcon(emoji, color) {
    return L.divIcon({
      html: `<div class="dot" style="background:${color};">${emoji}</div>`,
      className: "",
      iconSize: [24, 24],
      iconAnchor: [12, 12]
    });
  }

  _updateMarkers() {
    if (!this._map || !this._hass) return;
    
    // Clear old markers
    this._markers.forEach(m => m.remove());
    this._markers = [];

    for (const [id, stateObj] of Object.entries(this._hass.states)) {
      if (!id.startsWith("camera.wsdot_") && !id.startsWith("sensor.wsdot_")) continue;
      
      const attrs = stateObj.attributes;
      if (!attrs.latitude || !attrs.longitude) continue;

      let marker;
      if (id.startsWith("camera.")) {
        // Highway Camera
        const pic = attrs.entity_picture || "";
        marker = L.marker([attrs.latitude, attrs.longitude], { icon: this._createIcon("📷", "#3b82f6") })
          .bindPopup(
            `<div class="popup-content">
              <div class="popup-title">${attrs.friendly_name}</div>
              ${pic ? `<img class="popup-img" src="${pic}" onerror="this.style.display='none'" />` : ""}
            </div>`, 
            { maxWidth: 340 }
          );
      } else if (attrs.travel_time_id) {
        // Travel Time Route
        const avg = attrs.average_time_minutes || 1;
        const cur = parseFloat(stateObj.state) || 0;
        let color = "#10b981"; // Green
        if (cur / avg > 1.35) color = "#ef4444"; // Red
        else if (cur / avg > 1.1) color = "#f59e0b"; // Yellow
        
        marker = L.marker([attrs.latitude, attrs.longitude], { icon: this._createIcon("🚗", color) })
          .bindPopup(
            `<div class="popup-content">
              <div class="popup-title">${attrs.friendly_name}</div>
              <div class="popup-stat" style="color: ${color}; font-size: 16px; font-weight: bold;">${stateObj.state} min now</div>
              <div class="popup-stat" style="color: #94a3b8;">Avg: ${attrs.average_time_minutes} min</div>
            </div>`
          );
      } else if (attrs.pass_id) {
        // Mountain Pass
        marker = L.marker([attrs.latitude, attrs.longitude], { icon: this._createIcon("⛰️", "#8b5cf6") })
          .bindPopup(
            `<div class="popup-content">
              <div class="popup-title">${attrs.friendly_name}</div>
              <div class="popup-stat" style="color: #f59e0b;">${stateObj.state}</div>
              <div class="popup-stat">Temp: ${attrs.temperature}°F</div>
            </div>`
          );
      }

      if (marker) {
        marker.addTo(this._map);
        this._markers.push(marker);
      }
    }
  }
}

customElements.define("ha-panel-wsdot", WsdotPanel);
