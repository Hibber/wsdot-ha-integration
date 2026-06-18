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
