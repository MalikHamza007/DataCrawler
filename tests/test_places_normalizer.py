import pytest

from app.collectors.google_places.exceptions import GooglePlacesResponseError
from app.collectors.google_places.normalizer import normalize_place


def test_normalizer_extracts_google_place_fields() -> None:
    candidate = normalize_place(
        {
            "id": "abc",
            "displayName": {"text": "Example Heights"},
            "formattedAddress": "Lahore",
            "location": {"latitude": 31.5, "longitude": 74.3},
            "primaryType": "establishment",
            "types": ["establishment", "point_of_interest"],
            "businessStatus": "OPERATIONAL",
            "googleMapsUri": "https://maps.google.com/?cid=abc",
        },
        source_method="text_search",
        source_query="apartment project in Lahore",
        source_cell_id="cell-1",
    )
    assert candidate.google_place_id == "abc"
    assert candidate.display_name == "Example Heights"
    assert candidate.formatted_address == "Lahore"
    assert candidate.types == ["establishment", "point_of_interest"]


def test_normalizer_allows_missing_optional_fields_and_rejects_missing_required() -> None:
    candidate = normalize_place({"id": "abc", "displayName": {"text": "Name"}}, source_method="text_search", source_query=None, source_cell_id=None)
    assert candidate.latitude is None

    with pytest.raises(GooglePlacesResponseError):
        normalize_place({"displayName": {"text": "Name"}}, source_method="text_search", source_query=None, source_cell_id=None)
    with pytest.raises(GooglePlacesResponseError):
        normalize_place({"id": "abc", "displayName": {"text": ""}}, source_method="text_search", source_query=None, source_cell_id=None)
