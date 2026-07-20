(function () {
  async function request(path, options = {}) {
    const response = await fetch(path, {
      headers: { "Content-Type": "application/json", ...(options.headers || {}) },
      ...options
    });
    let data = null;
    const text = await response.text();
    if (text) {
      data = JSON.parse(text);
    }
    if (!response.ok) {
      const message = data && data.detail ? formatDetail(data.detail) : "The request failed.";
      throw new Error(message);
    }
    return data;
  }

  function formatDetail(detail) {
    if (Array.isArray(detail)) {
      return detail.map((item) => item.msg || item.message || "Validation error").join(" ");
    }
    return String(detail);
  }

  window.AlduorApi = {
    fetchMapConfig: () => request("/api/map-config"),
    fetchLahoreZones: () => request("/api/lahore-zones"),
    createCollectionJob: (payload) => request("/api/collection-jobs", { method: "POST", body: JSON.stringify(payload) }),
    listCollectionJobs: (params = {}) => {
      const query = new URLSearchParams({ limit: "20", ...params });
      return request(`/api/collection-jobs?${query.toString()}`);
    },
    getCollectionJob: (id) => request(`/api/collection-jobs/${id}`),
    listCollectionJobLogs: (id) => request(`/api/collection-jobs/${id}/logs`),
    cancelCollectionJob: (id) => request(`/api/collection-jobs/${id}/cancel`, { method: "POST" }),
    retryCollectionJob: (id) => request(`/api/collection-jobs/${id}/retry`, { method: "POST" }),
    fetchWorkerStatus: () => request("/api/worker-status"),
    fetchPlacesStatus: () => request("/api/places/status"),
    previewPlacesPlan: (id) => request(`/api/collection-jobs/${id}/places-plan`, { method: "POST" }),
    runDiscovery: (id) => request(`/api/collection-jobs/${id}/run-discovery`, { method: "POST" }),
    previewWebsite: (payload) => request("/api/website-enrichment/preview", { method: "POST", body: JSON.stringify(payload) }),
    createWebsiteJob: (payload) => request("/api/website-enrichment-jobs", { method: "POST", body: JSON.stringify(payload) }),
    getWebsiteCrawl: (id) => request(`/api/website-crawls/${id}`),
    getWebsitePages: (id) => request(`/api/website-crawls/${id}/pages`),
    getWebsiteEvidence: (id) => request(`/api/website-crawls/${id}/evidence`),
    listAssessments: () => request("/api/classification-assessments?limit=100"),
    reviewAssessment: (id, action, payload) => request(`/api/classification-assessments/${id}/${action}`, { method: "POST", body: JSON.stringify(payload) }),
    listRelationships: () => request("/api/project-developer-relationships?limit=100"),
    reviewRelationship: (id, action, payload = {}) => request(`/api/project-developer-relationships/${id}/${action}`, { method: "POST", body: JSON.stringify(payload) }),
    listDuplicates: () => request("/api/duplicate-candidates?limit=100"),
    reviewDuplicate: (id, action, payload) => request(`/api/duplicate-candidates/${id}/${action}`, { method: "POST", body: JSON.stringify(payload) }),
    listSocialCaptures: (params = {}) => {
      const query = new URLSearchParams({ limit: "25", ...params });
      return request(`/api/social-captures?${query.toString()}`);
    },
    getSocialCapture: (id) => request(`/api/social-captures/${id}`),
    attachSocialCapture: (id, payload) => request(`/api/social-captures/${id}/attach`, { method: "POST", body: JSON.stringify(payload) }),
    reviewSocialCapture: (id, action, payload = {}) => request(`/api/social-captures/${id}/${action}`, { method: "POST", body: JSON.stringify(payload) })
  };
})();
