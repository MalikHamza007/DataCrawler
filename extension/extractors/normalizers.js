(function () {
  function normalizeUsername(value) {
    return window.AlduorExtractors.cleanText(value || "", 255).replace(/^@/, "");
  }

  function phoneCandidates(text) {
    const matches = String(text || "").match(/(?:\+92|0092|92|0)?3\d{2}[\s().-]?\d{7}|\+92[\s().-]?\d{2,4}[\s().-]?\d{6,8}/g) || [];
    return window.AlduorExtractors.unique(matches.map((value) => ({ value, label: "Visible phone" })), window.AlduorExtractors.LIMITS.contacts);
  }

  function emailCandidates(text) {
    const matches = String(text || "").match(/[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}/gi) || [];
    return window.AlduorExtractors.unique(matches.map((value) => ({ value, label: "Visible email" })), window.AlduorExtractors.LIMITS.contacts);
  }

  function projectNames(text) {
    const matches = String(text || "").match(/\b[A-Z][A-Za-z0-9&'. -]{2,60}\s(?:Heights|Residencia|Residences|Towers|Tower|Mall|Arcade|Enclave|Courtyard|Apartments|Homes|Villas)\b/g) || [];
    return window.AlduorExtractors.unique(matches, window.AlduorExtractors.LIMITS.projects);
  }

  function addressCandidates(text) {
    const lines = String(text || "").split(/\n|\. /).filter((line) => /lahore|gulberg|dha|johar|bahria|model town|boulevard|road|avenue|block/i.test(line));
    return window.AlduorExtractors.unique(lines.map((line) => window.AlduorExtractors.cleanText(line, 500)), window.AlduorExtractors.LIMITS.addresses);
  }

  window.AlduorExtractors.normalizers = { normalizeUsername, phoneCandidates, emailCandidates, projectNames, addressCandidates };
})();

