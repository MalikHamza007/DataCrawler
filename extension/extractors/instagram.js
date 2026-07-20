(function () {
  function extractInstagram() {
    const A = window.AlduorExtractors;
    const parts = location.pathname.split("/").filter(Boolean);
    const pageKind = parts[0] === "p" || parts[0] === "reel" ? "public_post" : "business_profile";
    const capture = A.extractGeneric("instagram", pageKind, "instagram-v1");
    capture.username = A.normalizers.normalizeUsername(pageKind === "public_post" ? "" : parts[0] || "");
    const text = capture.visible_text_excerpt || "";
    if (/followers|following/i.test(text)) capture.warnings.push("Follower and following counts may be visible, but individual identities are not collected");
    if (/sponsored|learn more|shop now|book now/i.test(text)) {
      capture.page_kind = "promotional_post";
      capture.campaign = {
        campaign_type: "public_promotional_post",
        advertiser_name: capture.profile_name,
        campaign_text: text.slice(0, A.LIMITS.campaignText),
        call_to_action: (text.match(/learn more|shop now|book now|contact us/i) || [null])[0],
        destination_url: capture.websites[0] || null,
        visible_status: "status_not_visible",
        verification_status: "public_post_only"
      };
    }
    return capture;
  }

  window.AlduorExtractors.extractInstagram = extractInstagram;
})();

