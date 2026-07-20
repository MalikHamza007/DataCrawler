from __future__ import annotations

import gzip
from xml.etree import ElementTree


def parse_sitemap(content: bytes, *, max_urls: int = 500) -> tuple[list[str], list[str]]:
    if content[:2] == b"\x1f\x8b":
        content = gzip.decompress(content)
    try:
        root = ElementTree.fromstring(content)
    except ElementTree.ParseError:
        return [], []
    tag = root.tag.rsplit("}", 1)[-1]
    locations = [node.text.strip() for node in root.iter() if node.tag.rsplit("}", 1)[-1] == "loc" and node.text]
    if tag == "sitemapindex":
        return [], locations[:max_urls]
    return locations[:max_urls], []
