/**
 * WSDOT Traffic Lovelace Panel
 * Interactive map with highway cameras, travel times, and mountain pass conditions.
 * Uses Leaflet.js for the map and fetches live data from the WSDOT HA entities.
 */

import { LitElement, html, css } from "https://unpkg.com/lit@2.7.6/index.js?module";

class WsdotPanel extends LitElement {
  static properties = {
    hass: { type: Object },
    narrow: { type: Boolean },
    _selectedCamera: { state: true },
    _activeTab: { state: true },
    _filterText: { state: true },
    _mapReady: { state: true },
  };

  constructor() {
    super();
    this._selectedCamera = null;
    this._activeTab = "map";
    this._filterText = "";
    this._mapReady = false;
    this._map = null;
    this._cameraMarkers = new Map();
    this._passMarkers = new Map();
    this._leafletLoaded = false;
    this._refreshTimer = null;
  }

  static styles = css`
    :host {
      display: block;
      height: 100%;
      font-family: 'Inter', 'Roboto', sans-serif;
      --wsdot-bg: #0f1117;
      --wsdot-surface: #1a1d27;
      --wsdot-surface2: #22263a;
      --wsdot-accent: #3b82f6;
      --wsdot-accent2: #6366f1;
      --wsdot-green: #10b981;
      --wsdot-yellow: #f59e0b;
      --wsdot-red: #ef4444;
      --wsdot-orange: #f97316;
      --wsdot-text: #e2e8f0;
      --wsdot-text-muted: #94a3b8;
      --wsdot-border: rgba(255,255,255,0.08);
      background: var(--wsdot-bg);
      color: var(--wsdot-text);
    }

    .panel-root {
      display: flex;
      flex-direction: column;
      height: 100vh;
      overflow: hidden;
    }

    /* ---- Header ---- */
    .header {
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 12px 20px;
      background: linear-gradient(135deg, #1a1d27 0%, #0f1117 100%);
      border-bottom: 1px solid var(--wsdot-border);
      flex-shrink: 0;
      z-index: 100;
    }

    .header-logo {
      width: 36px;
      height: 36px;
      background: linear-gradient(135deg, var(--wsdot-accent), var(--wsdot-accent2));
      border-radius: 8px;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 18px;
      flex-shrink: 0;
    }

    .header-title {
      flex: 1;
    }

    .header-title h1 {
      margin: 0;
      font-size: 18px;
      font-weight: 700;
      background: linear-gradient(135deg, #e2e8f0, #94a3b8);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
    }

    .header-title p {
      margin: 0;
      font-size: 11px;
      color: var(--wsdot-text-muted);
    }

    .header-stats {
      display: flex;
      gap: 16px;
    }

    .stat-pill {
      display: flex;
      align-items: center;
      gap: 6px;
      padding: 6px 12px;
      background: var(--wsdot-surface2);
      border-radius: 20px;
      font-size: 12px;
      border: 1px solid var(--wsdot-border);
    }

    .stat-dot {
      width: 8px;
      height: 8px;
      border-radius: 50%;
      animation: pulse 2s infinite;
    }

    .stat-dot.green { background: var(--wsdot-green); }
    .stat-dot.yellow { background: var(--wsdot-yellow); }
    .stat-dot.red { background: var(--wsdot-red); }

    @keyframes pulse {
      0%, 100% { opacity: 1; }
      50% { opacity: 0.4; }
    }

    /* ---- Tab bar ---- */
    .tab-bar {
      display: flex;
      gap: 4px;
      padding: 8px 20px;
      background: var(--wsdot-surface);
      border-bottom: 1px solid var(--wsdot-border);
      flex-shrink: 0;
    }

    .tab {
      padding: 7px 16px;
      border-radius: 8px;
      border: none;
      background: transparent;
      color: var(--wsdot-text-muted);
      font-size: 13px;
      font-weight: 500;
      cursor: pointer;
      transition: all 0.2s ease;
      display: flex;
      align-items: center;
      gap: 6px;
    }

    .tab:hover {
      background: var(--wsdot-surface2);
      color: var(--wsdot-text);
    }

    .tab.active {
      background: linear-gradient(135deg, var(--wsdot-accent), var(--wsdot-accent2));
      color: white;
      font-weight: 600;
    }

    /* ---- Content area ---- */
    .content {
      flex: 1;
      display: flex;
      overflow: hidden;
    }

    /* ---- Map tab ---- */
    .map-container {
      flex: 1;
      display: flex;
      position: relative;
    }

    #wsdot-map {
      flex: 1;
      background: #1a2035;
    }

    .map-overlay {
      position: absolute;
      top: 12px;
      left: 12px;
      z-index: 400;
      display: flex;
      flex-direction: column;
      gap: 8px;
    }

    .map-legend {
      background: rgba(15,17,23,0.92);
      backdrop-filter: blur(12px);
      border: 1px solid var(--wsdot-border);
      border-radius: 10px;
      padding: 12px 14px;
      font-size: 12px;
    }

    .legend-title {
      font-weight: 600;
      margin-bottom: 8px;
      color: var(--wsdot-text);
    }

    .legend-item {
      display: flex;
      align-items: center;
      gap: 8px;
      margin-bottom: 5px;
      color: var(--wsdot-text-muted);
    }

    .legend-dot {
      width: 10px;
      height: 10px;
      border-radius: 50%;
      flex-shrink: 0;
    }

    /* ---- Camera modal ---- */
    .camera-modal-backdrop {
      position: fixed;
      inset: 0;
      background: rgba(0,0,0,0.85);
      backdrop-filter: blur(8px);
      z-index: 10000;
      display: flex;
      align-items: center;
      justify-content: center;
      animation: fadeIn 0.2s ease;
    }

    @keyframes fadeIn {
      from { opacity: 0; }
      to { opacity: 1; }
    }

    .camera-modal {
      background: var(--wsdot-surface);
      border: 1px solid var(--wsdot-border);
      border-radius: 16px;
      overflow: hidden;
      max-width: 720px;
      width: 90vw;
      animation: slideUp 0.3s cubic-bezier(0.34,1.56,0.64,1);
      box-shadow: 0 25px 80px rgba(0,0,0,0.8);
    }

    @keyframes slideUp {
      from { transform: translateY(30px) scale(0.96); opacity: 0; }
      to { transform: translateY(0) scale(1); opacity: 1; }
    }

    .camera-modal-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 16px 20px;
      border-bottom: 1px solid var(--wsdot-border);
      background: var(--wsdot-surface2);
    }

    .camera-modal-title {
      font-size: 15px;
      font-weight: 600;
    }

    .camera-modal-meta {
      font-size: 12px;
      color: var(--wsdot-text-muted);
      margin-top: 2px;
    }

    .close-btn {
      background: rgba(255,255,255,0.08);
      border: none;
      color: var(--wsdot-text);
      width: 32px;
      height: 32px;
      border-radius: 50%;
      cursor: pointer;
      font-size: 16px;
      display: flex;
      align-items: center;
      justify-content: center;
      transition: background 0.2s;
    }

    .close-btn:hover { background: rgba(255,255,255,0.15); }

    .camera-modal-body {
      padding: 0;
    }

    .camera-modal-img {
      width: 100%;
      display: block;
      background: #000;
      min-height: 200px;
    }

    .camera-modal-img.loading {
      min-height: 300px;
      display: flex;
      align-items: center;
      justify-content: center;
      color: var(--wsdot-text-muted);
      font-size: 14px;
    }

    .camera-modal-footer {
      padding: 12px 20px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      background: var(--wsdot-surface2);
      border-top: 1px solid var(--wsdot-border);
    }

    .camera-meta-chips {
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
    }

    .chip {
      padding: 3px 10px;
      border-radius: 12px;
      font-size: 11px;
      background: var(--wsdot-surface);
      border: 1px solid var(--wsdot-border);
      color: var(--wsdot-text-muted);
    }

    .refresh-btn {
      padding: 6px 14px;
      border-radius: 8px;
      border: none;
      background: linear-gradient(135deg, var(--wsdot-accent), var(--wsdot-accent2));
      color: white;
      font-size: 12px;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 6px;
      font-weight: 500;
      transition: opacity 0.2s;
    }

    .refresh-btn:hover { opacity: 0.85; }

    /* ---- Travel Times tab ---- */
    .data-tab {
      flex: 1;
      overflow-y: auto;
      padding: 16px;
      display: flex;
      flex-direction: column;
      gap: 12px;
    }

    .section-header {
      font-size: 13px;
      font-weight: 600;
      color: var(--wsdot-text-muted);
      text-transform: uppercase;
      letter-spacing: 0.08em;
      margin-bottom: 4px;
    }

    .search-bar {
      display: flex;
      align-items: center;
      gap: 10px;
      background: var(--wsdot-surface2);
      border: 1px solid var(--wsdot-border);
      border-radius: 10px;
      padding: 8px 14px;
    }

    .search-bar input {
      flex: 1;
      background: none;
      border: none;
      outline: none;
      color: var(--wsdot-text);
      font-size: 14px;
    }

    .search-bar input::placeholder { color: var(--wsdot-text-muted); }

    .route-card {
      background: var(--wsdot-surface);
      border: 1px solid var(--wsdot-border);
      border-radius: 12px;
      padding: 14px 16px;
      transition: all 0.2s ease;
      cursor: default;
    }

    .route-card:hover {
      border-color: rgba(59,130,246,0.3);
      box-shadow: 0 0 0 1px rgba(59,130,246,0.15);
    }

    .route-header {
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
      gap: 12px;
      margin-bottom: 10px;
    }

    .route-name {
      font-size: 14px;
      font-weight: 600;
      line-height: 1.3;
    }

    .route-desc {
      font-size: 12px;
      color: var(--wsdot-text-muted);
      margin-top: 2px;
    }

    .time-badges {
      display: flex;
      gap: 8px;
      flex-shrink: 0;
    }

    .time-badge {
      text-align: center;
      padding: 6px 10px;
      border-radius: 8px;
      min-width: 50px;
    }

    .time-badge.current {
      background: rgba(59,130,246,0.15);
      border: 1px solid rgba(59,130,246,0.3);
    }

    .time-badge.current.slow {
      background: rgba(239,68,68,0.15);
      border-color: rgba(239,68,68,0.3);
    }

    .time-badge.current.moderate {
      background: rgba(245,158,11,0.15);
      border-color: rgba(245,158,11,0.3);
    }

    .time-badge.average {
      background: rgba(16,185,129,0.1);
      border: 1px solid rgba(16,185,129,0.2);
    }

    .time-val {
      font-size: 18px;
      font-weight: 700;
      line-height: 1;
    }

    .time-label {
      font-size: 10px;
      color: var(--wsdot-text-muted);
      margin-top: 2px;
    }

    .time-badge.current .time-val { color: var(--wsdot-accent); }
    .time-badge.current.slow .time-val { color: var(--wsdot-red); }
    .time-badge.current.moderate .time-val { color: var(--wsdot-yellow); }
    .time-badge.average .time-val { color: var(--wsdot-green); }

    .route-progress {
      height: 4px;
      border-radius: 2px;
      background: var(--wsdot-surface2);
      overflow: hidden;
      margin-top: 8px;
    }

    .route-progress-fill {
      height: 100%;
      border-radius: 2px;
      transition: width 0.5s ease;
    }

    /* ---- Pass Conditions tab ---- */
    .pass-card {
      background: var(--wsdot-surface);
      border: 1px solid var(--wsdot-border);
      border-radius: 12px;
      padding: 14px 16px;
      transition: all 0.2s ease;
    }

    .pass-card:hover {
      border-color: rgba(99,102,241,0.3);
    }

    .pass-header {
      display: flex;
      align-items: center;
      gap: 12px;
      margin-bottom: 10px;
    }

    .pass-icon {
      font-size: 24px;
      flex-shrink: 0;
    }

    .pass-name {
      font-size: 14px;
      font-weight: 600;
    }

    .pass-elevation {
      font-size: 11px;
      color: var(--wsdot-text-muted);
    }

    .pass-status-badge {
      margin-left: auto;
      padding: 4px 10px;
      border-radius: 20px;
      font-size: 11px;
      font-weight: 600;
    }

    .pass-status-badge.ok {
      background: rgba(16,185,129,0.15);
      color: var(--wsdot-green);
      border: 1px solid rgba(16,185,129,0.3);
    }

    .pass-status-badge.advisory {
      background: rgba(245,158,11,0.15);
      color: var(--wsdot-yellow);
      border: 1px solid rgba(245,158,11,0.3);
    }

    .pass-condition {
      font-size: 12px;
      color: var(--wsdot-text-muted);
      line-height: 1.5;
    }

    .pass-chips {
      display: flex;
      gap: 8px;
      margin-top: 10px;
      flex-wrap: wrap;
    }

    .pass-chip {
      padding: 3px 10px;
      border-radius: 12px;
      font-size: 11px;
      background: var(--wsdot-surface2);
      color: var(--wsdot-text-muted);
      border: 1px solid var(--wsdot-border);
    }

    .pass-chip.temp { color: #60a5fa; }

    /* ---- Camera grid tab ---- */
    .camera-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
      gap: 12px;
    }

    .camera-thumb {
      background: var(--wsdot-surface);
      border: 1px solid var(--wsdot-border);
      border-radius: 12px;
      overflow: hidden;
      cursor: pointer;
      transition: all 0.25s ease;
    }

    .camera-thumb:hover {
      border-color: var(--wsdot-accent);
      transform: translateY(-2px);
      box-shadow: 0 8px 30px rgba(59,130,246,0.2);
    }

    .camera-thumb img {
      width: 100%;
      height: 180px;
      object-fit: cover;
      display: block;
      background: #0a0e1a;
    }

    .camera-thumb-info {
      padding: 10px 12px;
    }

    .camera-thumb-title {
      font-size: 13px;
      font-weight: 600;
      margin-bottom: 3px;
    }

    .camera-thumb-road {
      font-size: 11px;
      color: var(--wsdot-text-muted);
    }

    /* ---- Scrollbar styling ---- */
    ::-webkit-scrollbar { width: 6px; height: 6px; }
    ::-webkit-scrollbar-track { background: transparent; }
    ::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.15); border-radius: 3px; }
    ::-webkit-scrollbar-thumb:hover { background: rgba(255,255,255,0.25); }

    /* ---- Responsive ---- */
    @media (max-width: 600px) {
      .header-stats { display: none; }
      .camera-grid { grid-template-columns: 1fr; }
    }
  `;

  // -----------------------------------------------------------------------
  // Lifecycle
  // -----------------------------------------------------------------------

  firstUpdated() {
    this._loadLeaflet();
    // Auto-refresh every 60s
    this._refreshTimer = setInterval(() => this._refreshMapData(), 60000);
  }

  disconnectedCallback() {
    super.disconnectedCallback();
    if (this._refreshTimer) clearInterval(this._refreshTimer);
  }

  updated(changedProps) {
    if (changedProps.has("_activeTab") && this._activeTab === "map") {
      setTimeout(() => {
        if (this._map) {
          this._map.invalidateSize();
        } else {
          this._initMap();
        }
      }, 100);
    }
  }

  // -----------------------------------------------------------------------
  // Data helpers
  // -----------------------------------------------------------------------

  _getEntitiesByIntegration() {
    if (!this.hass) return { cameras: [], travelTimes: [], passes: [] };

    const cameras = [];
    const travelTimes = [];
    const passes = [];

    for (const [entityId, state] of Object.entries(this.hass.states)) {
      if (!entityId.startsWith("sensor.wsdot_") && !entityId.startsWith("camera.wsdot_")) continue;

      const attrs = state.attributes || {};

      if (entityId.startsWith("camera.wsdot_")) {
        cameras.push({ entityId, state, attrs });
      } else if (entityId.startsWith("sensor.wsdot_") && attrs.travel_time_id !== undefined && entityId.includes("_current")) {
        travelTimes.push({ entityId, state, attrs });
      } else if (entityId.startsWith("sensor.wsdot_") && attrs.pass_id !== undefined && entityId.includes("_condition")) {
        passes.push({ entityId, state, attrs });
      }
    }

    return { cameras, travelTimes, passes };
  }

  _congestionColor(current, average) {
    if (!current || !average || average === 0) return "#6366f1";
    const ratio = current / average;
    if (ratio < 1.1) return "#10b981";
    if (ratio < 1.35) return "#f59e0b";
    return "#ef4444";
  }

  _congestionClass(current, average) {
    if (!current || !average || average === 0) return "";
    const ratio = current / average;
    if (ratio >= 1.35) return "slow";
    if (ratio >= 1.1) return "moderate";
    return "";
  }

  // -----------------------------------------------------------------------
  // Leaflet map
  // -----------------------------------------------------------------------

  async _loadLeaflet() {
    if (this._leafletLoaded) {
      this._initMap();
      return;
    }

    // Inject Leaflet CSS
    if (!document.querySelector("#leaflet-css")) {
      const link = document.createElement("link");
      link.id = "leaflet-css";
      link.rel = "stylesheet";
      link.href = "https://unpkg.com/leaflet@1.9.4/dist/leaflet.css";
      document.head.appendChild(link);
    }

    // Load Leaflet JS
    if (!window.L) {
      await new Promise((resolve, reject) => {
        const script = document.createElement("script");
        script.src = "https://unpkg.com/leaflet@1.9.4/dist/leaflet.js";
        script.onload = resolve;
        script.onerror = reject;
        document.head.appendChild(script);
      });
    }

    this._leafletLoaded = true;
    this._initMap();
  }

  _initMap() {
    const mapEl = this.shadowRoot.querySelector("#wsdot-map");
    if (!mapEl || !window.L || this._map) return;

    // Dark tile layer (CartoDB Dark Matter)
    this._map = L.map(mapEl, {
      center: [47.5, -120.5],
      zoom: 7,
      zoomControl: true,
    });

    L.tileLayer(
      "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png",
      {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a> &copy; <a href="https://carto.com/attributions">CARTO</a> | WSDOT Traffic API',
        subdomains: "abcd",
        maxZoom: 19,
      }
    ).addTo(this._map);

    this._mapReady = true;
    this._refreshMapData();
  }

  _refreshMapData() {
    if (!this._map || !window.L) return;
    const { cameras, travelTimes, passes } = this._getEntitiesByIntegration();
    this._addCameraMarkers(cameras);
    this._addPassMarkers(passes);
    this._addTravelTimeMarkers(travelTimes);
  }

  _createCircleIcon(color, emoji = "📷", size = 32) {
    return L.divIcon({
      className: "",
      html: `
        <div style="
          width:${size}px;height:${size}px;
          background:${color};
          border:2px solid rgba(255,255,255,0.8);
          border-radius:50%;
          display:flex;align-items:center;justify-content:center;
          font-size:${size * 0.45}px;
          box-shadow:0 2px 8px rgba(0,0,0,0.6);
          cursor:pointer;
          transition:transform 0.15s;
        ">${emoji}</div>`,
      iconSize: [size, size],
      iconAnchor: [size / 2, size / 2],
    });
  }

  _addCameraMarkers(cameras) {
    // Remove old markers not in current set
    const currentIds = new Set(cameras.map(c => c.entityId));
    for (const [id, marker] of this._cameraMarkers) {
      if (!currentIds.has(id)) {
        marker.remove();
        this._cameraMarkers.delete(id);
      }
    }

    for (const cam of cameras) {
      const { entityId, state, attrs } = cam;
      const lat = attrs.latitude;
      const lon = attrs.longitude;
      if (!lat || !lon) continue;

      if (this._cameraMarkers.has(entityId)) continue;

      const marker = L.marker([lat, lon], {
        icon: this._createCircleIcon("rgba(59,130,246,0.9)", "📷", 28),
        zIndexOffset: 100,
      });

      marker.bindTooltip(attrs.title || entityId, {
        permanent: false,
        className: "wsdot-tooltip",
        direction: "top",
        offset: [0, -14],
      });

      marker.on("click", () => {
        this._selectedCamera = {
          entityId,
          title: attrs.title || entityId,
          imageUrl: attrs.image_url,
          roadName: attrs.road_name,
          direction: attrs.direction,
          milepost: attrs.milepost,
          region: attrs.region,
          owner: attrs.camera_owner,
        };
      });

      marker.addTo(this._map);
      this._cameraMarkers.set(entityId, marker);
    }
  }

  _addPassMarkers(passes) {
    for (const pass of passes) {
      const { entityId, state, attrs } = pass;
      const lat = attrs.latitude;
      const lon = attrs.longitude;
      if (!lat || !lon) continue;

      if (this._passMarkers.has(entityId)) {
        // Update tooltip
        const marker = this._passMarkers.get(entityId);
        marker.setTooltipContent(
          `<b>${attrs.pass_name || entityId}</b><br>${state.state || ""}`
        );
        continue;
      }

      const advisory = attrs.travel_advisory_active;
      const color = advisory ? "rgba(245,158,11,0.9)" : "rgba(16,185,129,0.9)";

      const marker = L.marker([lat, lon], {
        icon: this._createCircleIcon(color, "⛰️", 32),
        zIndexOffset: 200,
      });

      marker.bindTooltip(
        `<b>${attrs.pass_name || entityId}</b><br>${(state.state || "").substring(0, 80)}`,
        { permanent: false, direction: "top", offset: [0, -16] }
      );

      marker.addTo(this._map);
      this._passMarkers.set(entityId, marker);
    }
  }

  _addTravelTimeMarkers(travelTimes) {
    // Draw line markers for travel time endpoints
    for (const tt of travelTimes) {
      const { entityId, state, attrs } = tt;
      const startLat = attrs.start_latitude;
      const startLon = attrs.start_longitude;
      const endLat = attrs.end_latitude;
      const endLon = attrs.end_longitude;
      if (!startLat || !startLon || !endLat || !endLon) continue;

      if (this._map._layers) {
        // Skip if already drawn (simple check)
        const layerId = `tt_${entityId}`;
        if (this._map[layerId]) continue;
      }

      const current = parseFloat(state.state);
      const average = attrs.average_time_minutes || parseFloat(state.state);
      // We use the "current" sensor — look up average from attrs
      const color = this._congestionColor(current, average);

      const line = L.polyline(
        [[startLat, startLon], [endLat, endLon]],
        {
          color,
          weight: 3,
          opacity: 0.7,
          dashArray: "6, 4",
        }
      );

      line.bindTooltip(
        `<b>${attrs.route_name || entityId}</b><br>Current: ${current} min | Avg: ${average} min`,
        { direction: "center" }
      );

      line.addTo(this._map);
    }
  }

  // -----------------------------------------------------------------------
  // Render helpers
  // -----------------------------------------------------------------------

  _renderStats() {
    const { cameras, travelTimes, passes } = this._getEntitiesByIntegration();
    const congested = travelTimes.filter(tt => {
      const cur = parseFloat(tt.state.state);
      const avg = tt.attrs.average_time_minutes;
      return avg && cur / avg > 1.25;
    }).length;
    const advisories = passes.filter(p => p.attrs.travel_advisory_active).length;

    return html`
      <div class="header-stats">
        <div class="stat-pill">
          <div class="stat-dot green"></div>
          ${cameras.length} Cameras
        </div>
        <div class="stat-pill">
          <div class="stat-dot ${congested > 0 ? "red" : "green"}"></div>
          ${congested} Congested
        </div>
        <div class="stat-pill">
          <div class="stat-dot ${advisories > 0 ? "yellow" : "green"}"></div>
          ${advisories} Advisories
        </div>
      </div>
    `;
  }

  _renderCameraModal() {
    if (!this._selectedCamera) return html``;
    const cam = this._selectedCamera;

    return html`
      <div class="camera-modal-backdrop" @click=${(e) => {
        if (e.target === e.currentTarget) this._selectedCamera = null;
      }}>
        <div class="camera-modal">
          <div class="camera-modal-header">
            <div>
              <div class="camera-modal-title">${cam.title}</div>
              <div class="camera-modal-meta">
                ${cam.roadName ? `${cam.roadName}` : ""}
                ${cam.direction ? ` · ${cam.direction}` : ""}
                ${cam.milepost ? ` · MP ${cam.milepost}` : ""}
              </div>
            </div>
            <button class="close-btn" @click=${() => this._selectedCamera = null}>✕</button>
          </div>
          <div class="camera-modal-body">
            <img
              class="camera-modal-img"
              src="${cam.imageUrl}?t=${Date.now()}"
              alt="${cam.title}"
              @error=${(e) => { e.target.src = ""; e.target.style.minHeight = "200px"; }}
            />
          </div>
          <div class="camera-modal-footer">
            <div class="camera-meta-chips">
              ${cam.region ? html`<span class="chip">Region: ${cam.region}</span>` : ""}
              ${cam.owner ? html`<span class="chip">${cam.owner}</span>` : ""}
            </div>
            <button class="refresh-btn" @click=${() => {
              const img = this.shadowRoot.querySelector(".camera-modal-img");
              if (img) img.src = `${cam.imageUrl}?t=${Date.now()}`;
            }}>
              🔄 Refresh
            </button>
          </div>
        </div>
      </div>
    `;
  }

  _renderMapTab() {
    return html`
      <div class="map-container">
        <div id="wsdot-map"></div>
        <div class="map-overlay">
          <div class="map-legend">
            <div class="legend-title">📍 Map Legend</div>
            <div class="legend-item"><div class="legend-dot" style="background:#3b82f6"></div>Highway Camera</div>
            <div class="legend-item"><div class="legend-dot" style="background:#10b981"></div>Pass — Open</div>
            <div class="legend-item"><div class="legend-dot" style="background:#f59e0b"></div>Pass — Advisory</div>
            <div class="legend-item"><div class="legend-dot" style="background:#10b981;border-radius:0;height:3px;width:16px"></div>Route — Normal</div>
            <div class="legend-item"><div class="legend-dot" style="background:#f59e0b;border-radius:0;height:3px;width:16px"></div>Route — Moderate</div>
            <div class="legend-item"><div class="legend-dot" style="background:#ef4444;border-radius:0;height:3px;width:16px"></div>Route — Heavy</div>
          </div>
        </div>
      </div>
    `;
  }

  _renderTravelTimesTab() {
    const { travelTimes } = this._getEntitiesByIntegration();
    const filter = this._filterText.toLowerCase();

    const filtered = travelTimes.filter(tt => {
      const name = (tt.attrs.route_name || tt.entityId).toLowerCase();
      return !filter || name.includes(filter);
    });

    // Sort by congestion ratio descending
    filtered.sort((a, b) => {
      const ratioA = a.attrs.congestion_ratio || 1;
      const ratioB = b.attrs.congestion_ratio || 1;
      return ratioB - ratioA;
    });

    return html`
      <div class="data-tab">
        <div class="search-bar">
          🔍
          <input
            type="text"
            placeholder="Filter routes…"
            .value=${this._filterText}
            @input=${(e) => this._filterText = e.target.value}
          />
        </div>
        <div class="section-header">Travel Times (${filtered.length})</div>
        ${filtered.map(tt => this._renderTravelTimeCard(tt))}
        ${filtered.length === 0 ? html`<div style="color:var(--wsdot-text-muted);text-align:center;padding:40px">No routes match</div>` : ""}
      </div>
    `;
  }

  _renderTravelTimeCard(tt) {
    const { entityId, state, attrs } = tt;
    const current = parseFloat(state.state);
    // Try to get average from the same device's average sensor
    const avgEntityId = entityId.replace("_current_travel_time", "_average_travel_time");
    const avgState = this.hass?.states?.[avgEntityId];
    const average = avgState ? parseFloat(avgState.state) : (attrs.average_time_minutes || current);
    const ratio = average > 0 ? current / average : 1;
    const delay = Math.max(0, current - average);
    const fillPct = Math.min(100, (ratio / 2) * 100);
    const fillColor = this._congestionColor(current, average);
    const congClass = this._congestionClass(current, average);

    return html`
      <div class="route-card">
        <div class="route-header">
          <div>
            <div class="route-name">${attrs.route_name || entityId}</div>
            <div class="route-desc">${attrs.start_description || ""} → ${attrs.end_description || ""}</div>
          </div>
          <div class="time-badges">
            <div class="time-badge current ${congClass}">
              <div class="time-val">${isNaN(current) ? "—" : Math.round(current)}</div>
              <div class="time-label">Now</div>
            </div>
            <div class="time-badge average">
              <div class="time-val">${isNaN(average) ? "—" : Math.round(average)}</div>
              <div class="time-label">Avg</div>
            </div>
          </div>
        </div>
        ${delay > 0 ? html`
          <div style="font-size:12px;color:var(--wsdot-yellow);margin-bottom:6px">
            ⚠️ +${Math.round(delay)} min delay
          </div>
        ` : ""}
        <div class="route-progress">
          <div class="route-progress-fill" style="width:${fillPct}%;background:${fillColor}"></div>
        </div>
      </div>
    `;
  }

  _renderPassesTab() {
    const { passes } = this._getEntitiesByIntegration();
    const filter = this._filterText.toLowerCase();

    const filtered = passes.filter(p => {
      const name = (p.attrs.pass_name || p.entityId).toLowerCase();
      return !filter || name.includes(filter);
    });

    return html`
      <div class="data-tab">
        <div class="search-bar">
          🔍
          <input
            type="text"
            placeholder="Filter passes…"
            .value=${this._filterText}
            @input=${(e) => this._filterText = e.target.value}
          />
        </div>
        <div class="section-header">Mountain Passes (${filtered.length})</div>
        ${filtered.map(p => this._renderPassCard(p))}
      </div>
    `;
  }

  _renderPassCard(pass) {
    const { entityId, state, attrs } = pass;
    const advisory = attrs.travel_advisory_active;
    const tempEntityId = entityId.replace("_road_condition", "_temperature");
    const tempState = this.hass?.states?.[tempEntityId];
    const temp = tempState ? parseFloat(tempState.state) : null;
    const condition = (state.state || "").substring(0, 200);

    return html`
      <div class="pass-card">
        <div class="pass-header">
          <div class="pass-icon">⛰️</div>
          <div>
            <div class="pass-name">${attrs.pass_name || entityId}</div>
            <div class="pass-elevation">${attrs.elevation_feet ? `${attrs.elevation_feet.toLocaleString()} ft elevation` : ""}</div>
          </div>
          <div class="pass-status-badge ${advisory ? "advisory" : "ok"}">
            ${advisory ? "⚠️ Advisory" : "✅ Open"}
          </div>
        </div>
        <div class="pass-condition">${condition || "No current information"}</div>
        <div class="pass-chips">
          ${temp !== null ? html`<div class="pass-chip temp">🌡️ ${temp}°F</div>` : ""}
          ${attrs.restriction_one && attrs.restriction_one !== "No restrictions" && attrs.restriction_one !== "No current information available"
            ? html`<div class="pass-chip">⚠️ ${attrs.restriction_one_direction}: ${attrs.restriction_one}</div>` : ""}
          ${attrs.restriction_two && attrs.restriction_two !== "No restrictions" && attrs.restriction_two !== "No current information available"
            ? html`<div class="pass-chip">⚠️ ${attrs.restriction_two_direction}: ${attrs.restriction_two}</div>` : ""}
        </div>
      </div>
    `;
  }

  _renderCamerasTab() {
    const { cameras } = this._getEntitiesByIntegration();
    const filter = this._filterText.toLowerCase();

    const filtered = cameras.filter(c => {
      const title = (c.attrs.title || c.entityId).toLowerCase();
      const road = (c.attrs.road_name || "").toLowerCase();
      return !filter || title.includes(filter) || road.includes(filter);
    });

    return html`
      <div class="data-tab">
        <div class="search-bar">
          🔍
          <input
            type="text"
            placeholder="Filter cameras…"
            .value=${this._filterText}
            @input=${(e) => this._filterText = e.target.value}
          />
        </div>
        <div class="section-header">Highway Cameras (${filtered.length})</div>
        <div class="camera-grid">
          ${filtered.slice(0, 100).map(cam => html`
            <div class="camera-thumb" @click=${() => {
              this._selectedCamera = {
                entityId: cam.entityId,
                title: cam.attrs.title || cam.entityId,
                imageUrl: cam.attrs.image_url,
                roadName: cam.attrs.road_name,
                direction: cam.attrs.direction,
                milepost: cam.attrs.milepost,
                region: cam.attrs.region,
                owner: cam.attrs.camera_owner,
              };
            }}>
              <img
                src="${cam.attrs.image_url}?t=${Math.floor(Date.now() / 60000)}"
                alt="${cam.attrs.title || cam.entityId}"
                loading="lazy"
                @error=${(e) => { e.target.style.display = "none"; }}
              />
              <div class="camera-thumb-info">
                <div class="camera-thumb-title">${cam.attrs.title || cam.entityId}</div>
                <div class="camera-thumb-road">
                  ${cam.attrs.road_name || ""} ${cam.attrs.direction ? `· ${cam.attrs.direction}` : ""} ${cam.attrs.milepost ? `· MP ${cam.attrs.milepost}` : ""}
                </div>
              </div>
            </div>
          `)}
        </div>
        ${filtered.length > 100 ? html`
          <div style="text-align:center;color:var(--wsdot-text-muted);font-size:13px;padding:16px">
            Showing 100 of ${filtered.length} cameras. Use the filter to narrow results.
          </div>
        ` : ""}
      </div>
    `;
  }

  render() {
    return html`
      <link rel="preconnect" href="https://fonts.googleapis.com">
      <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">

      <div class="panel-root">
        <!-- Header -->
        <div class="header">
          <div class="header-logo">🚦</div>
          <div class="header-title">
            <h1>WSDOT Traffic</h1>
            <p>Washington State Department of Transportation · Live Data</p>
          </div>
          ${this._renderStats()}
        </div>

        <!-- Tab bar -->
        <div class="tab-bar">
          ${[
            { id: "map", label: "🗺️ Map", clear: true },
            { id: "travel", label: "🚗 Travel Times" },
            { id: "passes", label: "⛰️ Passes" },
            { id: "cameras", label: "📷 Cameras" },
          ].map(tab => html`
            <button
              class="tab ${this._activeTab === tab.id ? "active" : ""}"
              @click=${() => {
                this._activeTab = tab.id;
                this._filterText = "";
              }}
            >${tab.label}</button>
          `)}
        </div>

        <!-- Content -->
        <div class="content">
          ${this._activeTab === "map" ? this._renderMapTab() : ""}
          ${this._activeTab === "travel" ? this._renderTravelTimesTab() : ""}
          ${this._activeTab === "passes" ? this._renderPassesTab() : ""}
          ${this._activeTab === "cameras" ? this._renderCamerasTab() : ""}
        </div>

        <!-- Camera modal -->
        ${this._renderCameraModal()}
      </div>
    `;
  }
}

// Register the panel
customElements.define("wsdot-panel", WsdotPanel);

// Register as Lovelace panel
window.customPanels = window.customPanels || [];
window.customPanels.push({
  name: "wsdot-panel",
  tag: "wsdot-panel",
  url: "/local/wsdot-panel.js",
  embed_iframe: false,
});
