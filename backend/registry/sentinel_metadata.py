"""Curated location metadata for the Sentinel hackathon catalogue.

Catalogue names remain the source of truth for display names.  These helpers only
fill missing registry metadata so that a vendor's later manual corrections are
never overwritten by a catalogue refresh.
"""
import re


LEGACY_PROVENANCE = (
    "Approximate coordinates imported from the legacy Synetra Sentinel map; "
    "verify the exact camera position against a site survey"
)


# cam01-cam20 were already used by the Sentinel dashboard.  cam21-cam30 use
# documented place centroids because the catalogue does not publish camera GPS.
SENTINEL_COORDINATES: dict[str, tuple[float, float, str]] = {
    "cam01": (23.0225, 72.5714, LEGACY_PROVENANCE),
    "cam02": (23.0300, 72.5800, LEGACY_PROVENANCE),
    "cam03": (23.0400, 72.5200, LEGACY_PROVENANCE),
    "cam04": (23.0100, 72.5700, LEGACY_PROVENANCE),
    "cam05": (23.1000, 72.6200, LEGACY_PROVENANCE),
    "cam06": (21.5222, 70.4579, LEGACY_PROVENANCE),
    "cam07": (21.2900, 70.3800, LEGACY_PROVENANCE),
    "cam08": (21.5271, 70.4602, LEGACY_PROVENANCE),
    "cam09": (21.5350, 70.4700, LEGACY_PROVENANCE),
    "cam10": (21.5180, 70.4550, LEGACY_PROVENANCE),
    "cam11": (21.5120, 70.4500, LEGACY_PROVENANCE),
    "cam12": (23.1657, 72.5800, LEGACY_PROVENANCE),
    "cam13": (23.0200, 72.5600, LEGACY_PROVENANCE),
    "cam14": (23.0150, 72.5650, LEGACY_PROVENANCE),
    "cam15": (23.0250, 72.5750, LEGACY_PROVENANCE),
    "cam16": (23.1050, 72.6250, LEGACY_PROVENANCE),
    "cam17": (22.3039, 70.8022, LEGACY_PROVENANCE),
    "cam18": (22.3000, 70.7900, LEGACY_PROVENANCE),
    "cam19": (20.9700, 72.9000, LEGACY_PROVENANCE),
    "cam20": (22.3100, 70.8100, LEGACY_PROVENANCE),
    "cam21": (
        23.911516,
        72.318174,
        "Approximate Dethli place centroid from geographic.org; verify the exact camera position",
    ),
    "cam22": (
        23.64011,
        72.20845,
        "Approximate Mervada, Chanasma place centroid from Gram Vikas; verify the exact camera position",
    ),
    "cam23": (
        20.6300,
        73.0900,
        "Approximate Khergam, Navsari place centroid; catalogue label 'kheram' requires site verification",
    ),
    "cam24": (
        23.1691667,
        72.8100,
        "Approximate Dehgam place centroid from the Central Ground Water Board; verify the exact camera position",
    ),
    "cam25": (
        20.82902,
        73.01684,
        "Approximate Dhanori, Navsari place centroid from Bharat Broadband Network data; verify camera position",
    ),
    "cam26": (
        20.859107,
        73.127516,
        "Approximate Tankal, Navsari place centroid from geographic.org; verify the exact camera position",
    ),
    "cam27": (
        20.76957,
        72.96134,
        "Approximate Bilimora city centroid from GeoDatos; verify the exact camera position",
    ),
    "cam28": (
        20.76957,
        72.96134,
        "Approximate Bilimora city centroid from GeoDatos; verify the exact camera position",
    ),
    "cam29": (
        20.76957,
        72.96134,
        "Approximate Bilimora city centroid from GeoDatos; verify the exact camera position",
    ),
    "cam30": (
        23.07191,
        70.13153,
        "Approximate Gandhidham city centroid from Apple Maps; Rambaugh P2 requires site verification",
    ),
}


def catalogue_location(name: str) -> str:
    """Remove a catalogue sequence number and make separators readable."""
    without_sequence = re.sub(r"^\s*\d+\s+", "", name or "").strip()
    return " ".join(without_sequence.replace("-", " ").split())


def enrich_sentinel_camera(camera, catalogue_name: str) -> dict:
    """Fill missing Sentinel location fields and return the applied changes."""
    changes = {}
    if not camera.location:
        location = catalogue_location(catalogue_name)
        if location:
            camera.location = location
            changes["location"] = location

    coordinates = SENTINEL_COORDINATES.get(camera.external_id.lower())
    if coordinates and camera.latitude is None and camera.longitude is None:
        latitude, longitude, provenance = coordinates
        camera.latitude = latitude
        camera.longitude = longitude
        camera.location_provenance = provenance
        changes["coordinates"] = {
            "latitude": latitude,
            "longitude": longitude,
            "provenance": provenance,
        }
    return changes


def needs_sentinel_enrichment(camera, catalogue_name: str) -> bool:
    """Report whether sync would add location or coordinates without mutating."""
    needs_location = not camera.location and bool(catalogue_location(catalogue_name))
    has_known_coordinates = camera.external_id.lower() in SENTINEL_COORDINATES
    needs_coordinates = has_known_coordinates and camera.latitude is None and camera.longitude is None
    return needs_location or needs_coordinates
