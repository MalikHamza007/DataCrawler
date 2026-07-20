(function () {
  const labels = {};

  function initializeProjectTypes(projectTypes, defaultValues) {
    const container = document.getElementById("project-type-options");
    container.textContent = "";
    projectTypes.forEach((type) => {
      labels[type.value] = type.label;
      const label = document.createElement("label");
      label.className = "checkbox-item";
      const checkbox = document.createElement("input");
      checkbox.type = "checkbox";
      checkbox.value = type.value;
      checkbox.checked = defaultValues.includes(type.value);
      label.append(checkbox, document.createTextNode(type.label));
      container.appendChild(label);
    });
  }

  function selectedProjectTypes() {
    return Array.from(document.querySelectorAll("#project-type-options input:checked")).map((input) => input.value);
  }

  function setAllProjectTypes(checked) {
    document.querySelectorAll("#project-type-options input").forEach((input) => { input.checked = checked; });
  }

  function buildPayload(appState) {
    const projectTypes = selectedProjectTypes();
    if (projectTypes.length === 0) {
      throw new Error("Select at least one project type.");
    }
    const selectedZone = appState.selectedZone;
    const config = {
      search_mode: appState.searchMode,
      project_types: projectTypes
    };
    let lahoreZone = selectedZone ? selectedZone.name : null;
    if (appState.searchMode === "zone") {
      config.zone_id = selectedZone.id;
      config.radius_meters = appState.selectedRadiusMeters;
      config.map_center = selectedZone.center;
    }
    if (appState.searchMode === "radius") {
      config.radius_meters = appState.selectedRadiusMeters;
      config.map_center = selectedZone.center;
    }
    if (appState.searchMode === "rectangle" || appState.searchMode === "polygon") {
      config.geometry = appState.customGeometry;
      lahoreZone = null;
    }
    return {
      job_type: "places_discovery",
      city: "Lahore",
      lahore_zone: lahoreZone,
      search_config_json: config
    };
  }

  async function submitJob(appState) {
    const button = document.getElementById("start-search");
    button.disabled = true;
    button.textContent = "Creating collection job...";
    try {
      const payload = buildPayload(appState);
      const job = await AlduorApi.createCollectionJob(payload);
      window.AlduorApp.notify(`Collection job #${job.id} was created successfully.`, "success");
      await loadJobs();
      return job;
    } finally {
      button.disabled = false;
      button.textContent = "Start Search";
    }
  }

  async function loadJobs() {
    const jobs = await AlduorApi.listCollectionJobs();
    renderJobs(jobs);
    return jobs;
  }

  function renderJobs(jobs) {
    const body = document.getElementById("jobs-body");
    const empty = document.getElementById("jobs-empty");
    body.textContent = "";
    empty.style.display = jobs.length ? "none" : "block";
    jobs.forEach((job) => {
      const row = document.createElement("tr");
      row.append(
        td(`#${job.id}`),
        td(job.job_type === "website_enrichment" ? (job.search_config_json.seed_url || "Official website") : searchArea(job)),
        td(job.job_type === "website_enrichment" ? "Website enrichment" : typeLabels(job.search_config_json && job.search_config_json.project_types)),
        statusCell(job.status),
        td(job.progress_phase || ""),
        td(`${job.processed_items}/${job.total_items} - ${job.progress_percent || 0}% (${job.created_items} created, ${job.updated_items} updated, ${job.failed_items} failed)`),
        td(formatDate(job.created_at)),
        td(formatDate(job.updated_at)),
        actionCell(job)
      );
      body.appendChild(row);
    });
  }

  function td(text) {
    const cell = document.createElement("td");
    cell.textContent = text || "";
    return cell;
  }

  function statusCell(status) {
    const cell = document.createElement("td");
    const badge = document.createElement("span");
    badge.className = `status-badge status-${status}`;
    badge.textContent = status;
    cell.appendChild(badge);
    return cell;
  }

  function actionCell(job) {
    const cell = document.createElement("td");
    const button = document.createElement("button");
    button.type = "button";
    button.className = "secondary-button";
    button.textContent = "View";
    button.addEventListener("click", () => showJobDetails(job.id));
    cell.appendChild(button);
    if (job.is_cancellable) {
      const cancel = document.createElement("button");
      cancel.type = "button";
      cancel.className = "secondary-button";
      cancel.textContent = "Cancel";
      cancel.addEventListener("click", async () => {
        cancel.disabled = true;
        cancel.textContent = "Cancelling...";
        try {
          await AlduorApi.cancelCollectionJob(job.id);
          await loadJobs();
        } catch (error) {
          window.AlduorApp.notify(error.message, "error");
        }
      });
      cell.appendChild(cancel);
    }
    if (job.is_retryable) {
      const retry = document.createElement("button");
      retry.type = "button";
      retry.className = "secondary-button";
      retry.textContent = "Retry";
      retry.addEventListener("click", async () => {
        retry.disabled = true;
        try {
          await AlduorApi.retryCollectionJob(job.id);
          await loadJobs();
        } catch (error) {
          window.AlduorApp.notify(error.message, "error");
        }
      });
      cell.appendChild(retry);
    }
    return cell;
  }

  async function showJobDetails(id) {
    const [job, status, logs] = await Promise.all([AlduorApi.getCollectionJob(id), AlduorApi.fetchPlacesStatus(), AlduorApi.listCollectionJobLogs(id)]);
    const modal = document.getElementById("job-modal");
    const body = document.getElementById("job-modal-body");
    body.textContent = "";
    const note = document.createElement("p");
    note.textContent = job.job_type === "website_enrichment" ? "Official website crawl results and evidence." : "Google Places discovery details.";
    const statusLine = document.createElement("p");
    statusLine.textContent = `Google Places: enabled=${status.enabled}, configured=${status.configured}, dry_run=${status.dry_run}`;
    const buttons = document.createElement("div");
    buttons.className = "button-row";
    const planButton = document.createElement("button");
    planButton.type = "button";
    planButton.className = "secondary-button";
    planButton.textContent = "Preview Search Plan";
    const runButton = document.createElement("button");
    runButton.type = "button";
    runButton.className = "secondary-button";
    runButton.textContent = "Run Discovery";
    const output = document.createElement("pre");
    planButton.addEventListener("click", async () => {
      try {
        output.textContent = JSON.stringify(await AlduorApi.previewPlacesPlan(id), null, 2);
      } catch (error) {
        output.textContent = error.message;
      }
    });
    runButton.addEventListener("click", async () => {
      try {
        output.textContent = JSON.stringify(await AlduorApi.runDiscovery(id), null, 2);
        await loadJobs();
      } catch (error) {
        output.textContent = error.message;
      }
    });
    buttons.append(planButton, runButton);
    const details = document.createElement("pre");
    details.textContent = JSON.stringify(job, null, 2);
    const logTitle = document.createElement("h3");
    logTitle.textContent = "Recent Logs";
    const logBlock = document.createElement("pre");
    logBlock.textContent = JSON.stringify(logs, null, 2);
    body.append(note);
    if (job.job_type !== "website_enrichment") body.append(statusLine, buttons, output);
    body.append(details);
    if (job.website_crawl_id) {
      const [crawl, pages, evidence] = await Promise.all([AlduorApi.getWebsiteCrawl(job.website_crawl_id), AlduorApi.getWebsitePages(job.website_crawl_id), AlduorApi.getWebsiteEvidence(job.website_crawl_id)]);
      const crawlTitle = document.createElement("h3"); crawlTitle.textContent = "Website Crawl";
      const crawlBlock = document.createElement("pre"); crawlBlock.textContent = JSON.stringify({ crawl, pages, evidence }, null, 2);
      body.append(crawlTitle, crawlBlock);
    }
    body.append(logTitle, logBlock);
    modal.showModal();
  }

  async function loadWorkerStatus() {
    const element = document.getElementById("worker-status");
    const status = await AlduorApi.fetchWorkerStatus();
    element.textContent = status.status === "online"
      ? `Collector Worker: Online (${status.current_job_id ? `job #${status.current_job_id}` : "idle"})`
      : "Collector Worker: Offline. Start it with: python -m app.workers.runner";
    element.className = `worker-status ${status.status}`;
    return status;
  }

  function searchArea(job) {
    const config = job.search_config_json || {};
    if (job.lahore_zone) return job.lahore_zone;
    if (config.search_mode === "polygon") return "Custom polygon";
    if (config.search_mode === "rectangle") return "Custom rectangle";
    return config.search_mode || "Unknown";
  }

  function typeLabels(values) {
    return (values || []).map((value) => labels[value] || value).join(", ");
  }

  function formatDate(value) {
    return value ? new Date(value).toLocaleString() : "";
  }

  window.AlduorJobs = { initializeProjectTypes, selectedProjectTypes, setAllProjectTypes, submitJob, loadJobs, loadWorkerStatus };
})();
