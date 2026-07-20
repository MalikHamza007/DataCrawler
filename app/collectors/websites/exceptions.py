class WebsiteCrawlerError(Exception):
    pass


class UnsafeURLError(WebsiteCrawlerError):
    pass


class RobotsBlockedError(WebsiteCrawlerError):
    pass


class TemporaryWebsiteError(WebsiteCrawlerError):
    pass


class SeedFetchError(WebsiteCrawlerError):
    pass


class UnsupportedContentError(WebsiteCrawlerError):
    pass


class ResponseTooLargeError(WebsiteCrawlerError):
    pass
