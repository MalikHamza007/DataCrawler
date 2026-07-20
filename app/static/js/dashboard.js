import { dashboardState } from "./state.js";
import { api } from "./dashboard-api.js";
import { badge, date, safeLink, td, text } from "./formatters.js";
import { clearCollectionSelection, finishPolygonSelection, initMap, loadMapProjects, selectMarker, startCircleSelection, startPolygonSelection, startRectangleSelection, updateCircleRadius, useRadiusArea, useVisibleArea } from "./dashboard-map.js";
import { notify } from "./notifications.js";

document.addEventListener("DOMContentLoaded", start);
document.addEventListener("alduor:open-project", (event) => openProjectDetail(event.detail.id));
window.addEventListener("alduor:dashboard-google-ready", () => initMap(selectProject));
window.addEventListener("alduor:dashboard-map-ready", updateCollectionControls);

async function start() {
  bindNavigation();
  bindFilters();
  bindDrawer();
  bindActions();
  bindCollectionActions();
  restoreFilters();
  await Promise.allSettled([loadSummary(), loadProjects(), loadDevelopers(), loadJobs(), loadCaptures("unassigned"), loadIntelligence("classifications"), loadRefinementSummary(), updateWorker(), initializeCollectionSearch()]);
  loadExports();
  if (window.google?.maps) initMap(selectProject);
  else if (!window.ALDUOR_CONFIG.googleMapsConfigured) document.getElementById("map-status").textContent = "Google Maps key is missing.";
}

function bindNavigation() {
  document.querySelectorAll(".nav-tab").forEach((button) => {
    button.addEventListener("click", () => {
      dashboardState.section = button.dataset.section;
      document.querySelectorAll(".nav-tab").forEach((item) => item.classList.toggle("is-active", item === button));
      document.querySelectorAll(".dashboard-section").forEach((section) => section.classList.toggle("is-active", section.id === `${dashboardState.section}-section`));
      history.replaceState(null, "", `?section=${dashboardState.section}`);
    });
  });
}

function bindFilters() {
  const form = document.getElementById("project-filters");
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    applyFilters();
  });
  form.querySelector("input[name='q']").addEventListener("input", debounce(applyFilters, 450));
  document.getElementById("reset-filters").addEventListener("click", () => {
    form.reset();
    dashboardState.filters = {};
    dashboardState.pagination.offset = 0;
    renderChips();
    loadProjects();
    loadSummary();
    loadMapProjects(selectProject);
  });
  document.getElementById("save-filters").addEventListener("click", () => {
    localStorage.setItem("alduor.dashboard.filters", JSON.stringify(dashboardState.filters));
    notify("Filters saved locally.");
  });
  document.getElementById("toggle-filters").addEventListener("click", () => form.classList.toggle("is-collapsed"));
}

function bindActions() {
  document.getElementById("refresh-projects").addEventListener("click", loadProjects);
  document.getElementById("refresh-developers").addEventListener("click", loadDevelopers);
  document.getElementById("refresh-jobs").addEventListener("click", loadJobs);
  document.getElementById("refresh-exports").addEventListener("click", loadExports);
  document.getElementById("preview-export").addEventListener("click", previewExport);
  document.getElementById("create-export").addEventListener("click", createExport);
  document.getElementById("prepare-refinement").addEventListener("click", prepareRefinement);
  document.getElementById("refresh-captures").addEventListener("click", () => loadCaptures(activeCaptureStatus()));
  document.getElementById("refresh-intelligence").addEventListener("click", () => loadIntelligence(activeIntelTab()));
  document.getElementById("bulk-needs-review").addEventListener("click", bulkNeedsReview);
  document.querySelectorAll("[data-capture-status]").forEach((button) => {
    button.addEventListener("click", () => {
      document.querySelectorAll("[data-capture-status]").forEach((item) => item.classList.toggle("is-active", item === button));
      loadCaptures(button.dataset.captureStatus);
    });
  });
  document.querySelectorAll("[data-intel]").forEach((button) => {
    button.addEventListener("click", () => {
      document.querySelectorAll("[data-intel]").forEach((item) => item.classList.toggle("is-active", item === button));
      loadIntelligence(button.dataset.intel);
    });
  });
}

function bindCollectionActions() {
  document.getElementById("collection-area-form").addEventListener("submit", (event) => {
    event.preventDefault();
    selectNamedCollectionArea();
  });
  document.getElementById("use-visible-area").addEventListener("click", () => {
    if (!useVisibleArea(collectionGeometryChanged, dashboardState.collectionConfig.service_boundary)) notify("Move the map over Lahore and try again.");
  });
  document.getElementById("collection-radius-km").addEventListener("input", () => {
    const radiusMeters = selectedRadiusMeters();
    if (updateCircleRadius(radiusMeters, collectionGeometryChanged)) {
      setCollectionInstruction(`Circle selected: ${Math.round(radiusMeters / 1000)} km radius. Ready to search.`);
    }
  });
  document.getElementById("draw-search-circle").addEventListener("click", () => {
    if (!startCircleSelection(selectedRadiusMeters(), collectionGeometryChanged, setCollectionInstruction)) notify("The map is not ready yet.");
    updateCollectionControls();
  });
  document.getElementById("draw-search-rectangle").addEventListener("click", () => {
    if (!startRectangleSelection(collectionGeometryChanged, setCollectionInstruction)) notify("The map is not ready yet.");
    updateCollectionControls();
  });
  document.getElementById("draw-search-polygon").addEventListener("click", () => {
    if (!startPolygonSelection(collectionGeometryChanged, setCollectionInstruction)) notify("The map is not ready yet.");
    updateCollectionControls();
  });
  document.getElementById("finish-search-polygon").addEventListener("click", () => {
    if (!finishPolygonSelection(collectionGeometryChanged)) notify("Select at least three polygon points first.");
  });
  document.getElementById("clear-search-area").addEventListener("click", () => clearCollectionSelection(collectionGeometryChanged));
  document.getElementById("start-area-search").addEventListener("click", startAreaSearch);
}

async function initializeCollectionSearch() {
  const [config, zonesResponse] = await Promise.all([api.mapConfig(), api.lahoreZones()]);
  dashboardState.collectionConfig = config;
  dashboardState.collectionZones = zonesResponse.items;
  const areaOptions = document.getElementById("collection-area-options");
  areaOptions.textContent = "";
  dashboardState.collectionZones.forEach((zone) => {
    const option = document.createElement("option");
    option.value = zone.name;
    areaOptions.appendChild(option);
  });
  const defaults = new Set(["apartments", "commercial", "mixed_use", "residential_tower", "housing_society"]);
  const container = document.getElementById("collection-project-types");
  container.textContent = "";
  dashboardState.collectionConfig.project_types.forEach((option) => {
    const label = document.createElement("label");
    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.value = option.value;
    checkbox.checked = defaults.has(option.value);
    checkbox.addEventListener("change", updateCollectionControls);
    label.append(checkbox, document.createTextNode(option.label));
    container.appendChild(label);
  });
  updateCollectionControls();
}

function selectNamedCollectionArea() {
  const input = document.getElementById("collection-area-input");
  const query = input.value.trim().toLowerCase();
  if (!query) return notify("Enter a Lahore area, such as Gulberg.");
  const zone = findCollectionZone(query);
  if (!zone) return notify("Choose a Lahore area from the suggestions, or draw a custom area on the map.");
  input.value = zone.name;
  if (!useRadiusArea(zone.center, selectedRadiusMeters(), collectionGeometryChanged)) return notify("That area could not be selected on the map.");
  setCollectionInstruction(`${zone.name} selected with ${Math.round(selectedRadiusMeters() / 1000)} km radius. Start the search when ready.`);
}

function findCollectionZone(query) {
  const normalized = query.trim().toLowerCase().replaceAll(/[^a-z0-9]+/g, " ");
  const compact = normalized.replaceAll(" ", "");
  const acronym = (zone) => zone.name.split(/\s+/).map((part) => part[0] || "").join("").toLowerCase();
  return dashboardState.collectionZones.find((item) => item.name.toLowerCase() === normalized || item.id.toLowerCase() === query || item.id.toLowerCase().replaceAll("_", "") === compact)
    || dashboardState.collectionZones.find((item) => acronym(item) === compact)
    || dashboardState.collectionZones.find((item) => item.name.toLowerCase().startsWith(normalized))
    || dashboardState.collectionZones.find((item) => item.name.toLowerCase().includes(normalized));
}

function selectedRadiusMeters() {
  const input = document.getElementById("collection-radius-km");
  const value = Number(input.value || 3);
  const allowed = (dashboardState.collectionConfig?.radius_options || [1000, 2000, 3000, 5000, 10000, 15000]).map((item) => item / 1000);
  const bounded = Math.min(Math.max(Number.isFinite(value) ? value : 3, Math.min(...allowed)), Math.max(...allowed));
  if (bounded !== value) input.value = String(bounded);
  return Math.round(bounded * 1000);
}

function selectedCollectionProjectTypes() {
  return Array.from(document.querySelectorAll("#collection-project-types input:checked")).map((input) => input.value);
}

function collectionGeometryChanged(geometry) {
  dashboardState.collectionGeometry = geometry;
  if (geometry?.type === "rectangle") {
    setCollectionInstruction("Rectangle selected. Choose project types and start the search.");
  } else if (geometry?.type === "radius") {
    setCollectionInstruction(`Circle selected: ${Math.round(geometry.radius_meters / 1000)} km radius. Ready to search.`);
  } else if (geometry?.type === "polygon") {
    setCollectionInstruction(`Polygon selected with ${geometry.coordinates.length} points. Ready to search.`);
  } else if (!dashboardState.collectionSelectionMode) {
    setCollectionInstruction("Select an area to search.");
  }
  updateCollectionControls();
}

function setCollectionInstruction(message) {
  document.getElementById("collection-area-status").textContent = message;
  updateCollectionControls();
}

function updateCollectionControls() {
  const mapReady = Boolean(dashboardState.map && dashboardState.collectionConfig);
  const hasGeometry = Boolean(dashboardState.collectionGeometry);
  const selectedTypes = selectedCollectionProjectTypes();
  const jobRunning = Boolean(dashboardState.activeCollectionJobId);
  const selectingArea = Boolean(dashboardState.collectionSelectionMode);
  document.getElementById("use-visible-area").disabled = !mapReady;
  document.getElementById("draw-search-circle").disabled = !mapReady;
  document.getElementById("draw-search-rectangle").disabled = !mapReady;
  document.getElementById("draw-search-polygon").disabled = !mapReady;
  document.getElementById("finish-search-polygon").disabled = dashboardState.collectionSelectionMode !== "polygon" || dashboardState.collectionSelectionPoints.length < 3;
  document.getElementById("clear-search-area").disabled = !hasGeometry && !dashboardState.collectionSelectionMode;
  document.getElementById("start-area-search").disabled = !hasGeometry || selectingArea || selectedTypes.length === 0 || jobRunning;
  document.getElementById("draw-search-circle").classList.toggle("is-active", dashboardState.collectionSelectionMode === "circle");
  document.getElementById("draw-search-rectangle").classList.toggle("is-active", dashboardState.collectionSelectionMode === "rectangle");
  document.getElementById("draw-search-polygon").classList.toggle("is-active", dashboardState.collectionSelectionMode === "polygon");
  document.getElementById("collection-type-summary").textContent = selectedTypes.length ? `Project types (${selectedTypes.length})` : "Select project types";
}

function bindDrawer() {
  document.getElementById("close-drawer").addEventListener("click", closeDrawer);
  document.addEventListener("keydown", (event) => { if (event.key === "Escape") closeDrawer(); });
}

function applyFilters() {
  const form = new FormData(document.getElementById("project-filters"));
  dashboardState.filters = Object.fromEntries(Array.from(form.entries()).filter(([, value]) => value));
  dashboardState.pagination.offset = 0;
  renderChips();
  loadProjects();
  loadSummary();
  loadMapProjects(selectProject);
}

function restoreFilters() {
  try {
    const stored = JSON.parse(localStorage.getItem("alduor.dashboard.filters") || "{}");
    dashboardState.filters = stored;
    Object.entries(stored).forEach(([key, value]) => {
      const input = document.querySelector(`[name='${key}']`);
      if (input) input.value = value;
    });
    renderChips();
  } catch (_) {
    dashboardState.filters = {};
  }
}

function renderChips() {
  const chips = document.getElementById("filter-chips");
  chips.textContent = "";
  Object.entries(dashboardState.filters).forEach(([key, value]) => {
    const chip = document.createElement("span");
    chip.className = "chip";
    chip.textContent = `${key}: ${value}`;
    chips.appendChild(chip);
  });
}

async function loadSummary() {
  const data = await api.summary(dashboardState.filters);
  const cards = [
    ["Total Active Projects", data.projects.total_active, {}],
    ["Approved Projects", data.projects.approved, { review_status: "approved" }],
    ["Needs Review", data.projects.needs_review, { review_status: "needs_review" }],
    ["Without Developer", data.projects.unassigned_developer, { developer_assignment: "missing" }],
    ["Pending Duplicates", data.intelligence.pending_duplicates, { has_pending_duplicate: true }],
    ["Pending Relationships", data.intelligence.pending_relationships, { has_pending_relationship: true }],
    ["Projects with Phone", data.data_completeness.with_phone, { has_phone: true }],
    ["With Campaign Evidence", data.data_completeness.with_campaign_evidence, { has_campaign_evidence: true }],
    ["Ready to Contact", data.outreach.ready_to_contact, { outreach_status: "ready_to_contact" }],
    ["Follow-up Due", data.follow_up_due, { outreach_status: "follow_up_due" }],
    ["Failed Jobs", data.jobs.failed, {}],
    ["Social Pending", data.social.pending, {}]
  ];
  const container = document.getElementById("summary-cards");
  container.textContent = "";
  cards.forEach(([label, value, filter]) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "summary-card";
    const strong = document.createElement("strong");
    strong.textContent = String(value);
    const span = document.createElement("span");
    span.textContent = label;
    button.append(strong, span);
    button.addEventListener("click", () => {
      dashboardState.filters = { ...dashboardState.filters, ...filter };
      loadProjects();
      loadSummary();
      renderChips();
    });
    container.appendChild(button);
  });
}

async function loadProjects() {
  const loading = document.getElementById("projects-loading");
  loading.hidden = false;
  try {
    const data = await api.projects({ ...dashboardState.filters, offset: dashboardState.pagination.offset, limit: dashboardState.pagination.limit, sort: dashboardState.sorting.field, direction: dashboardState.sorting.direction });
    renderProjects(data.items, data.pagination);
  } catch (error) {
    notify(`Projects could not be loaded. ${error.message}`);
  } finally {
    loading.hidden = true;
  }
}

function renderProjects(items, pagination) {
  const body = document.getElementById("projects-body");
  body.textContent = "";
  items.forEach((project) => {
    const row = document.createElement("tr");
    row.dataset.projectId = project.id;
    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.setAttribute("aria-label", `Select ${project.name}`);
    checkbox.addEventListener("change", () => checkbox.checked ? dashboardState.selectedRows.add(project.id) : dashboardState.selectedRows.delete(project.id));
    const selectCell = td(checkbox);
    const action = document.createElement("button");
    action.type = "button";
    action.className = "secondary";
    action.textContent = "View";
    action.addEventListener("click", () => openProjectDetail(project.id));
    row.append(selectCell, td(project.name), td(project.developer_id ? `Developer #${project.developer_id}` : "Unassigned"), td(project.lahore_zone), td(project.project_type), td(badge(project.review_status)), td(badge(project.outreach_status)), td(dataIcons(project)), td(warnings(project)), td(date(project.updated_at)), td(action));
    row.addEventListener("click", (event) => {
      if (event.target.tagName !== "BUTTON" && event.target.tagName !== "INPUT") selectProject(project.id, { openDrawer: false, row });
    });
    body.appendChild(row);
  });
  renderPagination(pagination);
}

function dataIcons(project) {
  const span = document.createElement("span");
  [["Website", project.official_website_url], ["Coordinates", project.latitude && project.longitude]].forEach(([label, present]) => {
    const item = document.createElement("span");
    item.className = "badge";
    item.textContent = present ? label : `No ${label}`;
    span.appendChild(item);
  });
  return span;
}

function warnings(project) {
  const span = document.createElement("span");
  if (!project.developer_id) span.appendChild(badge("No Developer"));
  if (project.review_status === "needs_review") span.appendChild(badge("Needs Review"));
  return span;
}

function renderPagination(pagination) {
  const element = document.getElementById("project-pagination");
  element.textContent = "";
  const label = document.createElement("span");
  label.textContent = `${pagination.returned} of ${pagination.total}`;
  const prev = pageButton("Previous", pagination.has_previous, () => { dashboardState.pagination.offset = Math.max(0, dashboardState.pagination.offset - dashboardState.pagination.limit); loadProjects(); });
  const next = pageButton("Next", pagination.has_next, () => { dashboardState.pagination.offset += dashboardState.pagination.limit; loadProjects(); });
  element.append(prev, label, next);
}

function pageButton(label, enabled, fn) {
  const button = document.createElement("button");
  button.type = "button";
  button.className = "secondary";
  button.textContent = label;
  button.disabled = !enabled;
  button.addEventListener("click", fn);
  return button;
}

async function selectProject(id, options = {}) {
  document.querySelectorAll("#projects-body tr").forEach((row) => row.classList.toggle("is-selected", Number(row.dataset.projectId) === id));
  if (options.openDrawer) await openProjectDetail(id);
}

async function openProjectDetail(id) {
  const data = await api.projectDetail(id);
  openDrawer(`Project #${id}`, renderRecordDetail(data, "project"));
  if (data.project) selectMarker(data.project);
}

async function loadDevelopers() {
  const data = await api.developers({ offset: 0, limit: 50 });
  const body = document.getElementById("developers-body");
  body.textContent = "";
  data.items.forEach((developer) => {
    const action = document.createElement("button");
    action.type = "button";
    action.className = "secondary";
    action.textContent = "View";
    action.addEventListener("click", () => openDeveloperDetail(developer.id));
    const row = document.createElement("tr");
    row.append(td(developer.name), td(developer.classification), td(badge(developer.review_status)), td(badge(developer.outreach_status)), td(date(developer.updated_at)), td(action));
    body.appendChild(row);
  });
}

async function openDeveloperDetail(id) {
  const data = await api.developerDetail(id);
  openDrawer(`Developer #${id}`, renderRecordDetail(data, "developer"));
}

function renderRecordDetail(data, entityType) {
  const container = document.createElement("div");
  const record = data[entityType];
  const tabs = document.createElement("div");
  tabs.className = "drawer-tabs";
  ["Overview", "Contacts", "Social", "Campaigns", "Evidence", "Intelligence", "Outreach", "History"].forEach((name) => {
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = name;
    tabs.appendChild(button);
  });
  const overview = document.createElement("section");
  overview.className = "record-card";
  overview.append(line("Name", record.name), line("Review", record.review_status), line("Outreach", record.outreach_status), line("Version", record.version_number));
  const actions = document.createElement("div");
  actions.className = "button-row";
  ["approved", "needs_review", "rejected", "excluded"].forEach((status) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "secondary";
    button.textContent = status.replaceAll("_", " ");
    button.addEventListener("click", () => reviewRecord(entityType, record, status));
    actions.appendChild(button);
  });
  const outreachForm = outreachEditor(entityType, record);
  const children = document.createElement("section");
  children.className = "record-card";
  children.append(line("Contacts", (data.contacts || []).length), line("Social profiles", (data.social_profiles || []).length), line("Source evidence", data.source_evidence_count || 0), line("Campaign evidence", data.campaign_evidence_count || 0));
  container.append(tabs, overview, actions, children, outreachForm, listSection("Outreach Timeline", data.outreach || []), listSection("History", data.history || []));
  return container;
}

function line(label, value) {
  const p = document.createElement("p");
  const strong = document.createElement("strong");
  strong.textContent = `${label}: `;
  const span = document.createElement("span");
  span.textContent = text(value, "None");
  p.append(strong, span);
  return p;
}

function listSection(title, items) {
  const section = document.createElement("section");
  section.className = "record-card";
  const heading = document.createElement("h3");
  heading.textContent = title;
  section.appendChild(heading);
  if (!items.length) section.appendChild(document.createTextNode("No records yet."));
  items.forEach((item) => section.appendChild(line(item.action_type || item.activity_type || "Record", item.note || item.status_after || item.created_at)));
  return section;
}

function outreachEditor(entityType, record) {
  const section = document.createElement("section");
  section.className = "record-card";
  const heading = document.createElement("h3");
  heading.textContent = "Add Outreach Activity";
  const note = document.createElement("textarea");
  note.placeholder = "Record manual outreach notes. No message is sent.";
  const status = document.createElement("select");
  ["contacted", "ready_to_contact", "follow_up_due", "interested", "onboarding", "onboarded", "not_interested", "do_not_contact"].forEach((value) => {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = value.replaceAll("_", " ");
    status.appendChild(option);
  });
  const save = document.createElement("button");
  save.type = "button";
  save.className = "primary";
  save.textContent = "Record Outreach";
  save.addEventListener("click", async () => {
    await api.outreach({ [`${entityType}_id`]: record.id, activity_type: "contact_attempt", channel: "none", direction: "internal", status_after: status.value, note: note.value });
    notify("Outreach activity recorded.");
    entityType === "project" ? openProjectDetail(record.id) : openDeveloperDetail(record.id);
    loadSummary();
  });
  section.append(heading, status, note, save);
  return section;
}

async function reviewRecord(entityType, record, status) {
  const note = status === "approved" || status === "needs_review" ? "Dashboard review action." : "Dashboard review reason required.";
  const payload = { review_status: status, review_note: note, expected_version: record.version_number };
  try {
    entityType === "project" ? await api.reviewProject(record.id, payload) : await api.reviewDeveloper(record.id, payload);
    notify("Review status updated.");
    loadProjects();
    loadDevelopers();
    loadSummary();
    entityType === "project" ? openProjectDetail(record.id) : openDeveloperDetail(record.id);
  } catch (error) {
    notify(error.message);
  }
}

function openDrawer(title, content) {
  const drawer = document.getElementById("detail-drawer");
  document.getElementById("drawer-title").textContent = title;
  const body = document.getElementById("drawer-content");
  body.textContent = "";
  body.appendChild(content);
  drawer.classList.add("is-open");
  drawer.setAttribute("aria-hidden", "false");
  document.getElementById("close-drawer").focus();
}

function closeDrawer() {
  const drawer = document.getElementById("detail-drawer");
  drawer.classList.remove("is-open");
  drawer.setAttribute("aria-hidden", "true");
}

async function loadCaptures(status) {
  const items = await api.captures(status);
  const body = document.getElementById("captures-body");
  body.textContent = "";
  items.forEach((capture) => {
    const actions = document.createElement("div");
    actions.className = "button-row";
    actions.appendChild(safeLink(capture.source_url, "Open Source"));
    const row = document.createElement("tr");
    row.append(td(capture.platform), td(capture.profile_name || capture.page_title), td(capture.page_kind), td(badge(capture.review_status)), td(safeLink(capture.source_url, "Source")), td(actions));
    body.appendChild(row);
  });
}

async function loadIntelligence(kind) {
  const container = document.getElementById("intelligence-results");
  container.textContent = "Loading intelligence...";
  const data = kind === "relationships" ? await api.relationships() : kind === "duplicates" ? await api.duplicates() : await api.assessments();
  container.textContent = "";
  if (!data.length) container.textContent = "No pending records.";
  data.forEach((item) => {
    const card = document.createElement("article");
    card.className = "record-card";
    card.append(line("ID", item.id), line("Status", item.status || item.assessment_status), line("Score", item.system_score || item.duplicate_score));
    container.appendChild(card);
  });
}

async function loadJobs() {
  const jobs = await api.jobs();
  const body = document.getElementById("jobs-body");
  body.textContent = "";
  jobs.forEach((job) => {
    const row = document.createElement("tr");
    row.append(td(job.id), td(job.job_type), td(badge(job.status)), td(job.progress_phase), td(`${job.processed_items || 0}/${job.total_items || 0}`), td(date(job.created_at)), td("Open logs"));
    body.appendChild(row);
  });
  return jobs;
}

async function startAreaSearch() {
  const button = document.getElementById("start-area-search");
  const status = document.getElementById("collection-job-status");
  button.disabled = true;
  button.textContent = "Checking...";
  status.textContent = "Validating the selected area and project types...";
  document.getElementById("collection-research-metrics").hidden = true;
  try {
    const geometry = dashboardState.collectionGeometry;
    const projectTypes = selectedCollectionProjectTypes();
    if (!geometry) throw new Error("Select a search area first.");
    if (dashboardState.collectionSelectionMode) throw new Error("Finish or clear the current area selection first.");
    if (!projectTypes.length) throw new Error("Select at least one project type.");
    if (!collectionGeometryInsideLahore(geometry)) throw new Error("The selected area must stay inside the Lahore service boundary.");
    const placesStatus = await api.placesStatus();
    if (!placesStatus.enabled || !placesStatus.text_search_available) {
      throw new Error("Google Places is not enabled/configured, so live project discovery cannot run yet.");
    }

    button.textContent = "Starting...";
    status.textContent = "Submitting the search to the collector...";
    const job = await api.createCollectionJob({
      job_type: "places_discovery",
      city: "Lahore",
      lahore_zone: null,
      search_config_json: {
        search_mode: geometry.type,
        project_types: projectTypes,
        ...(geometry.type === "radius"
          ? { map_center: geometry.map_center, radius_meters: geometry.radius_meters }
          : { geometry })
      }
    });
    dashboardState.activeCollectionJobId = job.id;
    document.getElementById("collection-job-status").textContent = `Research #${job.id} queued. Searching Google Places first, then discovered official websites.`;
    notify(`Area research #${job.id} started.`);
    updateCollectionControls();
    loadJobs();
    pollCollectionJob(job.id);
  } catch (error) {
    const message = error.message || "The search could not be started.";
    status.textContent = `Search could not start: ${message}`;
    notify(message);
  } finally {
    button.textContent = "Start Research";
    updateCollectionControls();
  }
}

function collectionGeometryInsideLahore(geometry) {
  const boundary = dashboardState.collectionConfig?.service_boundary;
  if (!boundary) return false;
  const points = geometry.type === "rectangle"
    ? [
        { lat: geometry.north, lng: geometry.east },
        { lat: geometry.north, lng: geometry.west },
        { lat: geometry.south, lng: geometry.east },
        { lat: geometry.south, lng: geometry.west }
      ]
    : geometry.type === "radius"
      ? radiusBoundaryPoints(geometry.map_center, geometry.radius_meters)
    : geometry.coordinates;
  return points.every((point) => point.lat <= boundary.north && point.lat >= boundary.south && point.lng <= boundary.east && point.lng >= boundary.west);
}

function radiusBoundaryPoints(center, radiusMeters) {
  const latDelta = radiusMeters / 111320;
  const lngDelta = radiusMeters / (111320 * Math.max(Math.cos(center.lat * Math.PI / 180), 0.2));
  return [
    { lat: center.lat + latDelta, lng: center.lng },
    { lat: center.lat - latDelta, lng: center.lng },
    { lat: center.lat, lng: center.lng + lngDelta },
    { lat: center.lat, lng: center.lng - lngDelta }
  ];
}

async function pollCollectionJob(jobId) {
  if (dashboardState.activeCollectionJobId !== jobId) return;
  try {
    const [job, summary] = await Promise.all([api.job(jobId), api.researchSummary(jobId)]);
    renderResearchSummary(summary);
    const progress = `${job.progress_percent || 0}%`;
    const detail = job.progress_message || job.progress_phase || job.status;
    const websiteDetail = job.error_message
      || (job.status === "completed" && summary.websites.pending
        ? `Reading official websites (${summary.websites.pending} remaining)`
        : detail);
    document.getElementById("collection-job-status").textContent = `Research #${job.id}: ${summary.status} - ${websiteDetail} (${progress})`;
    loadJobs();
    if (["completed", "completed_with_errors", "failed", "cancelled"].includes(summary.status)) {
      dashboardState.activeCollectionJobId = null;
      updateCollectionControls();
      if (["completed", "completed_with_errors"].includes(summary.status)) {
        notify(`Research #${job.id} finished after ${summary.resources_processed} sources. ${summary.results.projects_created} projects created.`);
        await Promise.allSettled([loadProjects(), loadMapProjects(selectProject), loadSummary()]);
      } else {
        notify(`Research #${job.id} ${summary.status}. ${job.error_message || "Open Collection Jobs for details."}`);
      }
      return;
    }
    window.setTimeout(() => pollCollectionJob(jobId), 2500);
  } catch (error) {
    document.getElementById("collection-job-status").textContent = `Job #${jobId}: status could not be refreshed. Retrying...`;
    window.setTimeout(() => pollCollectionJob(jobId), 4000);
  }
}

function renderResearchSummary(summary) {
  const container = document.getElementById("collection-research-metrics");
  const records = summary.results.projects_created
    + summary.results.developers_created
    + summary.results.contacts_created
    + summary.results.social_profiles_created;
  const values = [
    [summary.resources_processed, "Sources processed"],
    [summary.places.api_requests, "Google requests"],
    [summary.places.raw_results, "Places reviewed"],
    [`${summary.websites.completed}/${summary.websites.queued}`, "Websites processed"],
    [summary.websites.pages_visited, "Web pages read"],
    [records, "Records extracted"],
    [summary.errors, "Errors"]
  ];
  container.textContent = "";
  values.forEach(([value, label]) => {
    const metric = document.createElement("div");
    metric.className = "research-metric";
    const count = document.createElement("strong");
    count.textContent = String(value);
    const description = document.createElement("span");
    description.textContent = label;
    metric.append(count, description);
    container.appendChild(metric);
  });
  container.hidden = false;
}

function exportPayload() {
  const form = new FormData(document.getElementById("export-form"));
  const options = {};
  ["include_contacts", "include_social_profiles", "include_campaign_evidence", "include_source_evidence", "include_relationships", "include_duplicate_candidates", "include_outreach_activities", "include_collection_logs", "include_rejected_records", "include_excluded_records", "include_merged_records"].forEach((key) => {
    options[key] = form.get(key) === "on";
  });
  return {
    format: form.get("format"),
    scope: form.get("scope"),
    project_filters: { ...dashboardState.filters },
    developer_filters: {},
    options,
    filename_label: form.get("filename_label") || undefined
  };
}

async function loadRefinementSummary() {
  const container = document.getElementById("refinement-summary");
  try {
    const summary = await api.refinementSummary();
    container.textContent = `${summary.export_ready_projects} export-ready from ${summary.likely_real_estate_projects} likely projects (${summary.raw_projects} raw results).`;
  } catch (error) {
    container.textContent = `Refinement status unavailable: ${error.message}`;
  }
}

async function prepareRefinement() {
  const button = document.getElementById("prepare-refinement");
  button.disabled = true;
  try {
    const result = await api.prepareRefinement();
    notify(`Clean-data job #${result.refinement_job_id} queued after ${result.website_jobs_queued} website enrichment jobs.`);
    await loadJobs();
    await loadRefinementSummary();
  } catch (error) {
    notify(`Clean-data preparation failed. ${error.message}`);
  } finally {
    button.disabled = false;
  }
}

async function previewExport() {
  const payload = exportPayload();
  try {
    const preview = await api.exportPreview(payload);
    const container = document.getElementById("export-preview");
    container.textContent = "";
    container.append(
      line("Format", preview.format),
      line("Scope", preview.scope),
      line("Projects", preview.estimated.projects),
      line("Developers", preview.estimated.developers),
      line("Contacts", preview.estimated.project_contacts + preview.estimated.developer_contacts),
      line("Primary rows", preview.estimated_primary_rows),
      line("Within row limit", preview.within_row_limit ? "Yes" : "No")
    );
    if (preview.warnings.length) container.appendChild(listSection("Warnings", preview.warnings.map((warning) => ({ note: warning }))));
    document.getElementById("create-export").disabled = !preview.within_row_limit;
  } catch (error) {
    notify(`Export preview failed. ${error.message}`);
  }
}

async function createExport() {
  try {
    const artifact = await api.createExport(exportPayload());
    notify(`Export #${artifact.id} queued.`);
    document.getElementById("create-export").disabled = true;
    loadExports();
    pollExport(artifact.id);
  } catch (error) {
    notify(`Export could not be created. ${error.message}`);
  }
}

async function loadExports() {
  try {
    const data = await api.exports();
    const body = document.getElementById("exports-body");
    if (!body) return;
    body.textContent = "";
    data.items.forEach((artifact) => body.appendChild(exportRow(artifact)));
  } catch (error) {
    notify(`Exports could not be loaded. ${error.message}`);
  }
}

function exportRow(artifact) {
  const row = document.createElement("tr");
  const actions = document.createElement("div");
  actions.className = "button-row";
  if (artifact.status === "ready") {
    const download = document.createElement("a");
    download.href = `/api/exports/${artifact.id}/download`;
    download.textContent = "Download";
    actions.appendChild(download);
  }
  const retry = document.createElement("button");
  retry.type = "button";
  retry.className = "secondary";
  retry.textContent = "Retry";
  retry.disabled = !["failed", "cancelled", "expired", "deleted"].includes(artifact.status);
  retry.addEventListener("click", async () => { await api.retryExport(artifact.id); notify("Export retried."); loadExports(); });
  const del = document.createElement("button");
  del.type = "button";
  del.className = "secondary";
  del.textContent = "Delete";
  del.disabled = ["queued", "generating", "validating"].includes(artifact.status);
  del.addEventListener("click", async () => { await api.deleteExport(artifact.id); notify("Export deleted."); loadExports(); });
  actions.append(retry, del);
  row.append(td(artifact.id), td(artifact.filename), td(artifact.format), td(artifact.scope), td(badge(artifact.status)), td(artifact.row_count), td(artifact.file_size_bytes || ""), td(date(artifact.created_at)), td(date(artifact.expires_at)), td(artifact.download_count), td(actions));
  return row;
}

async function pollExport(id) {
  if (document.hidden) return;
  try {
    const artifact = await api.exportDetail(id);
    loadExports();
    if (["queued", "generating", "validating"].includes(artifact.status)) setTimeout(() => pollExport(id), 2000);
  } catch (_) {}
}

async function updateWorker() {
  try {
    const worker = await api.worker();
    const isOnline = worker.status === "online";
    document.getElementById("worker-indicator").textContent = isOnline ? "Worker: Online" : "Worker: Offline";
    document.getElementById("worker-status-detail").textContent = isOnline ? "Collector Worker: Online" : "Collector Worker: Offline. Start the worker with: python -m app.workers.runner";
  } catch (_) {
    document.getElementById("worker-indicator").textContent = "Worker: Offline";
  }
}

async function bulkNeedsReview() {
  const ids = Array.from(dashboardState.selectedRows);
  if (!ids.length) return notify("Select at least one project.");
  const result = await api.bulk({ entity_type: "project", entity_ids: ids, action: "set_review_status", payload: { review_status: "needs_review", note: "Bulk dashboard review." } });
  notify(`${result.updated} records updated. ${result.failed} failed.`);
  dashboardState.selectedRows.clear();
  loadProjects();
  loadSummary();
}

function activeCaptureStatus() {
  return document.querySelector("[data-capture-status].is-active")?.dataset.captureStatus || "unassigned";
}

function activeIntelTab() {
  return document.querySelector("[data-intel].is-active")?.dataset.intel || "classifications";
}

function debounce(fn, wait) {
  let timer = 0;
  return (...args) => {
    clearTimeout(timer);
    timer = setTimeout(() => fn(...args), wait);
  };
}
