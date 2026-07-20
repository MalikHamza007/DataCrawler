(function () {
  function extractLinkedIn() {
    const A = window.AlduorExtractors;
    const path = location.pathname.toLowerCase();
    if (/\/in\//.test(path)) {
      return { supported: false, reason: "private_or_unsupported_page", message: "LinkedIn personal profiles are not supported for Alduor capture." };
    }
    const pageKind = /\/posts\//.test(path) ? "public_post" : "company_page";
    const capture = A.extractGeneric("linkedin", pageKind, "linkedin-v1");
    if (!/\/company\/|\/school\/|\/showcase\//.test(path) && pageKind !== "public_post") {
      capture.warnings.push("LinkedIn page type is uncertain");
      capture.page_kind = "unknown_public_page";
    }
    return capture;
  }

  window.AlduorExtractors.extractLinkedIn = extractLinkedIn;
})();

