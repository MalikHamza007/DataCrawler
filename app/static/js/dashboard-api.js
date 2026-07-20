import { dashboardState } from "./state.js";

export async function request(key, path, options = {}) {
  if (dashboardState.activeRequests[key]) dashboardState.activeRequests[key].abort();
  const controller = new AbortController();
  dashboardState.activeRequests[key] = controller;
  try {
    const response = await fetch(path, {
      ...options,
      signal: controller.signal,
      headers: { "Content-Type": "application/json", ...(options.headers || {}) }
    });
    const text = await response.text();
    const data = text ? JSON.parse(text) : null;
    if (!response.ok) {
      const error = new Error(formatDetail(data && data.detail ? data.detail : "Request failed."));
      error.status = response.status;
      error.payload = data;
      throw error;
    }
    return data;
  } finally {
    if (dashboardState.activeRequests[key] === controller) delete dashboardState.activeRequests[key];
  }
}

export function formatDetail(detail) {
  if (Array.isArray(detail)) return detail.map((item) => item.msg || item.message || "Validation error").join(" ");
  return String(detail);
}

export function query(params) {
  const output = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") output.set(key, String(value));
  });
  return output.toString();
}

export const api = {
  summary: (filters) => request("summary", `/api/dashboard/summary?${query(filters)}`),
  projects: (params) => request("projects", `/api/dashboard/projects?${query(params)}`),
  developers: (params) => request("developers", `/api/dashboard/developers?${query(params)}`),
  mapProjects: (params) => request("map", `/api/map/projects?${query(params)}`),
  projectDetail: (id) => request("project-detail", `/api/projects/${id}/dashboard-detail`),
  developerDetail: (id) => request("developer-detail", `/api/developers/${id}/dashboard-detail`),
  reviewProject: (id, payload) => request("review-project", `/api/projects/${id}/review`, { method: "POST", body: JSON.stringify(payload) }),
  reviewDeveloper: (id, payload) => request("review-developer", `/api/developers/${id}/review`, { method: "POST", body: JSON.stringify(payload) }),
  outreach: (payload) => request("outreach-create", "/api/dashboard/outreach-activities", { method: "POST", body: JSON.stringify(payload) }),
  bulk: (payload) => request("bulk", "/api/dashboard/bulk-actions", { method: "POST", body: JSON.stringify(payload) }),
  captures: (status) => request("captures", `/api/social-captures?${query({ review_status: status, limit: 100 })}`),
  jobs: () => request("jobs", "/api/collection-jobs?limit=50"),
  job: (id) => request(`job-${id}`, `/api/collection-jobs/${id}`),
  researchSummary: (id) => request(`research-summary-${id}`, `/api/collection-jobs/${id}/research-summary`),
  createCollectionJob: (payload) => request("collection-job-create", "/api/collection-jobs", { method: "POST", body: JSON.stringify(payload) }),
  mapConfig: () => request("map-config", "/api/map-config"),
  lahoreZones: () => request("lahore-zones", "/api/lahore-zones"),
  placesStatus: () => request("places-status", "/api/places/status"),
  worker: () => request("worker", "/api/worker-status"),
  assessments: () => request("assessments", "/api/classification-assessments?limit=100"),
  relationships: () => request("relationships", "/api/project-developer-relationships?limit=100"),
  duplicates: () => request("duplicates", "/api/duplicate-candidates?limit=100")
  ,
  exportPreview: (payload) => request("export-preview", "/api/exports/preview", { method: "POST", body: JSON.stringify(payload) }),
  createExport: (payload) => request("export-create", "/api/exports", { method: "POST", body: JSON.stringify(payload) }),
  exports: () => request("exports", "/api/exports?limit=50"),
  exportDetail: (id) => request(`export-${id}`, `/api/exports/${id}`),
  refinementSummary: () => request("refinement-summary", "/api/refinement/summary"),
  prepareRefinement: () => request("refinement-job", "/api/refinement/jobs", { method: "POST" }),
  retryExport: (id) => request(`export-retry-${id}`, `/api/exports/${id}/retry`, { method: "POST" }),
  deleteExport: (id) => request(`export-delete-${id}`, `/api/exports/${id}`, { method: "DELETE" })
};
