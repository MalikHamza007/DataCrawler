(function () {
  function extractGeneric(platform = "generic", pageKind = "unknown_public_page", version = "generic-v1") {
    const A = window.AlduorExtractors;
    const capture = A.baseContract(platform, pageKind, version);
    const visibleBlocks = Array.from(document.querySelectorAll("h1,h2,h3,p,li,address,main,article,section"))
      .map(A.visibleText)
      .filter(Boolean);
    const visibleText = A.cleanText(visibleBlocks.join("\n"), A.LIMITS.text);
    const headings = Array.from(document.querySelectorAll("h1,h2,h3")).map(A.visibleText).filter(Boolean);
    const ogTitle = A.meta("og:title");
    const ogDescription = A.meta("og:description");
    capture.profile_name = headings[0] || ogTitle || capture.page_title;
    capture.visible_text_excerpt = visibleText || ogDescription;
    capture.about_text = ogDescription || visibleBlocks.slice(0, 5).join(" ");
    capture.phones = A.normalizers.phoneCandidates(visibleText);
    capture.emails = A.normalizers.emailCandidates(visibleText);
    capture.project_names = A.normalizers.projectNames(visibleText);
    capture.addresses = A.normalizers.addressCandidates(visibleText);
    const links = Array.from(document.querySelectorAll("a[href]")).filter(A.isVisible);
    capture.websites = A.unique(links.map((link) => A.safeUrl(link.href)).filter((url) => url && !sameHost(url)), A.LIMITS.links);
    capture.external_links = capture.websites.slice(0, A.LIMITS.links);
    capture.whatsapp = A.unique(links.filter((link) => /wa\.me|whatsapp/i.test(link.href)).map((link) => ({ value: A.cleanText(link.textContent || link.href), url: A.safeUrl(link.href) })), A.LIMITS.contacts);
    if (!capture.visible_text_excerpt && !capture.profile_name) capture.warnings.push("No visible business information was detected");
    return capture;
  }

  function sameHost(urlValue) {
    try {
      return new URL(urlValue).hostname === location.hostname;
    } catch (_) {
      return true;
    }
  }

  window.AlduorExtractors.extractGeneric = extractGeneric;
})();

