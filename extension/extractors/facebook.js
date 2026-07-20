(function () {
  function extractFacebook() {
    const A = window.AlduorExtractors;
    const path = location.pathname.toLowerCase();
    const pageKind = /\/posts\/|\/videos\/|story_fbid|permalink/.test(location.href) ? "public_post" : "business_profile";
    const capture = A.extractGeneric("facebook", pageKind, "facebook-v1");
    capture.username = A.normalizers.normalizeUsername(location.pathname.split("/").filter(Boolean)[0] || "");
    const buttons = Array.from(document.querySelectorAll("a,button")).filter(A.isVisible).map(A.visibleText).filter(Boolean);
    const cta = buttons.find((text) => /learn more|call now|send message|whatsapp|contact us|book now/i.test(text));
    if (pageKind === "public_post" && /sponsored|promoted|learn more|book now/i.test(`${capture.visible_text_excerpt} ${cta || ""}`)) {
      capture.page_kind = "promotional_post";
      capture.campaign = {
        campaign_type: "public_promotional_post",
        advertiser_name: capture.profile_name,
        campaign_text: capture.visible_text_excerpt.slice(0, A.LIMITS.campaignText),
        call_to_action: cta || null,
        destination_url: capture.websites[0] || null,
        visible_status: "status_not_visible",
        verification_status: "public_post_only"
      };
    }
    if (path.includes("/search/")) capture.page_kind = "search_result_page";
    return capture;
  }

  window.AlduorExtractors.extractFacebook = extractFacebook;
})();

