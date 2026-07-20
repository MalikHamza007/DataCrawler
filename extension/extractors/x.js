(function () {
  function extractX() {
    const A = window.AlduorExtractors;
    const parts = location.pathname.split("/").filter(Boolean);
    const pageKind = parts.includes("status") ? "public_post" : "business_profile";
    const capture = A.extractGeneric("x", pageKind, "x-v1");
    capture.username = A.normalizers.normalizeUsername(parts[0] || "");
    capture.websites = A.unique(capture.websites.concat(Array.from(document.querySelectorAll("a[href]")).filter(A.isVisible).map((link) => A.safeUrl(link.href)).filter((url) => url && !/x\.com|twitter\.com/.test(url))), A.LIMITS.links);
    return capture;
  }

  window.AlduorExtractors.extractX = extractX;
})();

