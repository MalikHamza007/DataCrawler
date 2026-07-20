TEXT_SEARCH_FIELD_MASK = (
    "places.id,places.displayName,places.formattedAddress,places.location,"
    "places.primaryType,places.types,places.businessStatus,places.googleMapsUri,"
    "places.websiteUri,places.nationalPhoneNumber,places.internationalPhoneNumber,nextPageToken"
)

NEARBY_SEARCH_FIELD_MASK = (
    "places.id,places.displayName,places.formattedAddress,places.location,"
    "places.primaryType,places.types,places.businessStatus,places.googleMapsUri,"
    "places.websiteUri,places.nationalPhoneNumber,places.internationalPhoneNumber"
)


def validate_field_mask(field_mask: str) -> str:
    if "*" in field_mask:
        raise ValueError("wildcard field masks are not allowed")
    return field_mask
