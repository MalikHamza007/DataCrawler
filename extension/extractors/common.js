(function () {
  const LIMITS = {
    text: 20000,
    about: 10000,
    campaignText: 10000,
    projects: 50,
    contacts: 30,
    addresses: 20,
    links: 100,
    warnings: 50
  };

  function isVisible(element) {
    if (!element || !element.isConnected || element.nodeType !== Node.ELEMENT_NODE) return false;
    if (element.closest("[aria-hidden='true']")) return false;
    const style = window.getComputedStyle(element);
    if (style.display === "none" || style.visibility === "hidden" || style.visibility === "collapse" || Number(style.opacity) === 0) return false;
    return element.getClientRects().length > 0;
  }

  function visibleText(element) {
    if (!isVisible(element)) return "";
    if (["SCRIPT", "STYLE", "NOSCRIPT", "TEMPLATE"].includes(element.tagName)) return "";
    return cleanText(element.innerText || element.textContent || "");
  }

  function cleanText(value, limit = 2048) {
    return String(value || "").replace(/[\u0000-\u0008\u000b\u000c\u000e-\u001f\u007f]/g, "").replace(/\s+/g, " ").trim().slice(0, limit);
  }

  function unique(values, limit) {
    const seen = new Set();
    const output = [];
    values.forEach((value) => {
      const text = typeof value === "string" ? cleanText(value) : value;
      const key = typeof text === "string" ? text.toLowerCase() : JSON.stringify(text);
      if (text && !seen.has(key) && output.length < limit) {
        seen.add(key);
        output.push(text);
      }
    });
    return output;
  }

  function safeUrl(value) {
    try {
      const url = new URL(value, location.href);
      if (!["http:", "https:"].includes(url.protocol)) return null;
      return url.href;
    } catch (_) {
      return null;
    }
  }

  function meta(name) {
    const selector = `meta[property="${name}"], meta[name="${name}"]`;
    return cleanText(document.querySelector(selector)?.getAttribute("content") || "", 10000);
  }

  function baseContract(platform, pageKind, extractorVersion) {
    const canonical = safeUrl(document.querySelector("link[rel='canonical']")?.href || location.href);
    return {
      capture_version: "1",
      platform,
      page_kind: pageKind || "unknown_public_page",
      source_url: safeUrl(location.href),
      canonical_url: canonical,
      page_title: cleanText(document.title, 255),
      profile_name: "",
      username: "",
      visible_text_excerpt: "",
      about_text: "",
      project_names: [],
      phones: [],
      emails: [],
      whatsapp: [],
      addresses: [],
      websites: [],
      external_links: [],
      campaign: null,
      captured_at: new Date().toISOString(),
      extractor_version: extractorVersion,
      warnings: []
    };
  }

  window.AlduorExtractors = window.AlduorExtractors || {};
  Object.assign(window.AlduorExtractors, { LIMITS, isVisible, visibleText, cleanText, unique, safeUrl, meta, baseContract });
})();

