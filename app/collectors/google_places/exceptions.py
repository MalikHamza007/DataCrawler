class GooglePlacesError(Exception):
    pass


class GooglePlacesConfigurationError(GooglePlacesError):
    pass


class GooglePlacesAuthenticationError(GooglePlacesError):
    pass


class GooglePlacesPermissionError(GooglePlacesError):
    pass


class GooglePlacesRateLimitError(GooglePlacesError):
    pass


class GooglePlacesInvalidRequestError(GooglePlacesError):
    pass


class GooglePlacesTimeoutError(GooglePlacesError):
    pass


class GooglePlacesServerError(GooglePlacesError):
    pass


class GooglePlacesResponseError(GooglePlacesError):
    pass


class SearchPlanLimitError(GooglePlacesError):
    pass


class SearchGeometryError(GooglePlacesError):
    pass
