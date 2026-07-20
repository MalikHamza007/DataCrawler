(function () {
  function detectPlatform(urlValue) {
    let url;
    try {
      url = new URL(urlValue || location.href);
    } catch (_) {
      return { platform: "unsupported", page_kind: "unknown", hostname: "" };
    }
    const hostname = url.hostname.toLowerCase().replace(/^www\./, "");
    if (!["http:", "https:"].includes(url.protocol)) return { platform: "unsupported", page_kind: "unknown", hostname };
    if ((hostname === "facebook.com" || hostname === "m.facebook.com") && url.pathname.startsWith("/ads/library")) {
      return { platform: "meta_ad_library", page_kind: "ad_library_result", hostname };
    }
    if (hostname === "facebook.com" || hostname === "m.facebook.com") return { platform: "facebook", page_kind: "unknown", hostname };
    if (hostname === "instagram.com") return { platform: "instagram", page_kind: "unknown", hostname };
    if (hostname === "x.com" || hostname === "twitter.com") return { platform: "x", page_kind: "unknown", hostname };
    if (hostname === "linkedin.com") return { platform: "linkedin", page_kind: "unknown", hostname };
    return { platform: "generic", page_kind: "unknown_public_page", hostname };
  }

  function unsupportedPageReason() {
    const text = document.body ? document.body.innerText.toLowerCase() : "";
    const path = location.pathname.toLowerCase();
    if (/login|captcha|checkpoint|access denied|log in to continue|rate limit/.test(text + " " + path)) return "private_or_unsupported_page";
    if (/messages|notifications|settings|followers|following|friends|groups\/.*members/.test(path)) return "private_or_unsupported_page";
    return "";
  }

  window.AlduorExtractors.detectPlatform = detectPlatform;
  window.AlduorExtractors.unsupportedPageReason = unsupportedPageReason;
})();

