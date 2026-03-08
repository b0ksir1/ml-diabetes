from __future__ import annotations

from geopy.exc import GeocoderServiceError, GeocoderTimedOut
from geopy.geocoders import Nominatim


def geocoding(address: str) -> dict[str, str] | None:
    """Resolve address to {'lat': '...', 'lng': '...'} or None."""
    if not address or not address.strip():
        return None

    addr = address.strip()
    geolocator = Nominatim(user_agent="stroke_app_kr", timeout=10)

    geo = _try_geocode(geolocator, addr)
    if geo is not None:
        return {"lat": str(geo.latitude), "lng": str(geo.longitude)}

    # Fallback for Korean addresses without country suffix.
    if "South Korea" not in addr and "Korea" not in addr and "대한민국" not in addr:
        geo = _try_geocode(geolocator, f"{addr}, South Korea")
        if geo is not None:
            return {"lat": str(geo.latitude), "lng": str(geo.longitude)}

    return None


def _try_geocode(geolocator: Nominatim, query: str):
    try:
        return geolocator.geocode(query)
    except (GeocoderTimedOut, GeocoderServiceError, AttributeError):
        return None
