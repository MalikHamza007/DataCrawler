from __future__ import annotations

from app.collectors.google_places.exceptions import GooglePlacesResponseError
from app.collectors.google_places.types import NormalizedPlaceCandidate


def normalize_place(place: dict, *, source_method: str, source_query: str | None, source_cell_id: str | None) -> NormalizedPlaceCandidate:
    google_place_id = place.get("id")
    if not google_place_id:
        raise GooglePlacesResponseError("Google place result is missing id.")
    display_name = (place.get("displayName") or {}).get("text")
    if not display_name or not display_name.strip():
        raise GooglePlacesResponseError("Google place result is missing display name.")
    location = place.get("location") or {}
    latitude = location.get("latitude")
    longitude = location.get("longitude")
    if latitude is not None and not -90 <= latitude <= 90:
        raise GooglePlacesResponseError("Google place latitude is invalid.")
    if longitude is not None and not -180 <= longitude <= 180:
        raise GooglePlacesResponseError("Google place longitude is invalid.")
    return NormalizedPlaceCandidate(
        google_place_id=google_place_id,
        display_name=display_name.strip(),
        formatted_address=place.get("formattedAddress"),
        latitude=latitude,
        longitude=longitude,
        primary_type=place.get("primaryType"),
        types=list(place.get("types") or []),
        business_status=place.get("businessStatus"),
        google_maps_url=place.get("googleMapsUri"),
        website_url=place.get("websiteUri"),
        national_phone_number=place.get("nationalPhoneNumber"),
        international_phone_number=place.get("internationalPhoneNumber"),
        source_method=source_method,
        source_query=source_query,
        source_cell_id=source_cell_id,
    )
