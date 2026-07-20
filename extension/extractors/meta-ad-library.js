(function () {
  function extractMetaAdLibrary() {
    const A = window.AlduorExtractors;
    const capture = A.extractGeneric("meta_ad_library", "ad_library_result", "meta-ad-library-v1");
    const text = capture.visible_text_excerpt || "";
    const cta = (text.match(/learn more|send message|book now|call now|contact us|whatsapp/i) || [null])[0];
    const active = /active|running/i.test(text);
    const inactive = /inactive|ended|not active/i.test(text);
    capture.campaign = {
      campaign_type: "meta_ad_library",
      advertiser_name: capture.profile_name,
      campaign_text: text.slice(0, A.LIMITS.campaignText),
      call_to_action: cta,
      destination_url: capture.websites[0] || null,
      visible_status: active ? "active_visible" : inactive ? "inactive_visible" : "status_not_visible",
      verification_status: "captured_from_ad_library"
    };
    return capture;
  }

  function captureVisiblePage() {
    const A = window.AlduorExtractors;
    const refusal = A.unsupportedPageReason();
    if (refusal) return { supported: false, reason: refusal };
    const detected = A.detectPlatform(location.href);
    if (detected.platform === "unsupported") return { supported: false, reason: "private_or_unsupported_page" };
    try {
      if (detected.platform === "meta_ad_library") return A.extractMetaAdLibrary();
      if (detected.platform === "facebook") return A.extractFacebook();
      if (detected.platform === "instagram") return A.extractInstagram();
      if (detected.platform === "x") return A.extractX();
      if (detected.platform === "linkedin") return A.extractLinkedIn();
      return A.extractGeneric("generic", "unknown_public_page", "generic-v1");
    } catch (error) {
      const fallback = A.extractGeneric(detected.platform === "unsupported" ? "generic" : detected.platform, "unknown_public_page", "generic-v1");
      fallback.warnings.push("Platform layout may have changed");
      return fallback;
    }
  }

  window.AlduorExtractors.extractMetaAdLibrary = extractMetaAdLibrary;
  window.AlduorExtractors.captureVisiblePage = captureVisiblePage;
})();

