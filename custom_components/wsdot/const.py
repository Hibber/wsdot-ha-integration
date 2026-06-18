"""Constants for the WSDOT Traffic integration."""

DOMAIN = "wsdot"
CONF_API_KEY = "api_key"
DEFAULT_SCAN_INTERVAL = 60  # seconds

WSDOT_API_BASE = "https://wsdot.wa.gov/Traffic/api"

TRAVEL_TIMES_URL = (
    f"{WSDOT_API_BASE}/TravelTimes/TravelTimesREST.svc/GetTravelTimesAsJson"
    "?AccessCode={api_key}"
)
PASS_CONDITIONS_URL = (
    f"{WSDOT_API_BASE}/MountainPassConditions/MountainPassConditionsREST.svc"
    "/GetMountainPassConditionsAsJson?AccessCode={api_key}"
)
CAMERAS_URL = (
    f"{WSDOT_API_BASE}/HighwayCameras/HighwayCamerasREST.svc/GetCamerasAsJson"
    "?AccessCode={api_key}"
)
FLOW_DATA_URL = (
    f"{WSDOT_API_BASE}/FlowData/FlowDataREST.svc/GetFlowDataAsJson"
    "?AccessCode={api_key}"
)

# Data keys used in coordinator
DATA_TRAVEL_TIMES = "travel_times"
DATA_PASS_CONDITIONS = "pass_conditions"
DATA_CAMERAS = "cameras"
DATA_FLOW = "flow"

# Sensor platforms
PLATFORMS = ["sensor", "camera", "binary_sensor"]

# Attribution
ATTRIBUTION = "Data provided by WSDOT (Washington State Department of Transportation)"

# Icon mappings
ICON_TRAVEL_TIME = "mdi:car-clock"
ICON_PASS = "mdi:mountain"
ICON_CAMERA = "mdi:cctv"
ICON_CONGESTION = "mdi:traffic-cone"
ICON_TEMPERATURE = "mdi:thermometer"
ICON_ADVISORY = "mdi:alert-circle"

# ---------------------------------------------------------------------------
# Local area filter — Olympia / Thurston County + key corridors
# ---------------------------------------------------------------------------
# Geographic bounding box: covers Olympia/Lacey/Tumwater + the I-5 corridor
# south of Tacoma down through Thurston County, and enough northward reach
# to include the Tacoma/JBLM segment that feeds into local commutes.
#
#   SW corner: ~46.7°N, -123.2°W  (south of Olympia toward Tenino)
#   NE corner: ~47.35°N, -122.2°W (south King County / Auburn area)
#
# This captures all cameras, flow stations, and travel time endpoints that
# are relevant to someone commuting from or within the Olympia area.
LOCAL_BBOX = {
    "lat_min": 46.70,
    "lat_max": 47.35,
    "lon_min": -123.20,
    "lon_max": -122.20,
}

# Road names (WSDOT internal codes) to include for travel time routes.
# Even if a route's start/end point is outside the bbox, include it if it
# runs along one of these key corridors that Olympia commuters use.
LOCAL_ROAD_NAMES = {
    "005",   # I-5
    "090",   # I-90 / Snoqualmie Pass
    "405",   # I-405 (Eastside)
    "167",   # SR-167 / Valley Freeway
    "520",   # SR-520
    "101",   # US-101 (Olympic Peninsula approach)
    "012",   # US-12 / White Pass (east of Olympia)
    "510",   # SR-510 (Yelm Hwy — Thurston County)
}

# Mountain pass IDs to always include regardless of location.
# These are the passes most relevant to Olympia-area travel.
# IDs from the API: 11=Snoqualmie, 10=Stevens, 12=White Pass, 13=Manastash
LOCAL_PASS_IDS = {11, 10, 12, 13}

