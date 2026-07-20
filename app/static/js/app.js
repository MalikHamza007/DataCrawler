(function () {
  const appState = {
    config: null,
    zones: [],
    selectedZone: null,
    selectedRadiusMeters: 5000,
    searchMode: "zone",
    customGeometry: null,
    mapInitialized: false
  };

  const defaultProjectTypes = ["apartments", "commercial", "mixed_use", "residential_tower", "housing_society"];

  async function start() {
    bindModal();
    try {
      const [config, zonesResponse] = await Promise.all([
        AlduorApi.fetchMapConfig(),
        AlduorApi.fetchLahoreZones()
      ]);
      appState.config = config;
      appState.zones = zonesResponse.items;
      appState.selectedZone = appState.zones[0];
      renderControls(config, appState.zones);
      bindControls();
      await AlduorJobs.loadJobs();
      await AlduorJobs.loadWorkerStatus();
      window.setInterval(() => {
        if (document.hidden) return;
        AlduorJobs.loadJobs().catch((error) => notify(error.message, "error"));
        AlduorJobs.loadWorkerStatus().catch(() => {});
      }, 5000);
      if (!window.ALDUOR_CONFIG.googleMapsConfigured) {
        document.getElementById("map-status").textContent = "Google Maps is not configured. Add GOOGLE_MAPS_BROWSER_API_KEY to the .env file.";
      } else {
        initializeGoogleMapIfReady();
        window.setTimeout(() => {
          if (!appState.mapInitialized) {
            document.getElementById("map-status").textContent = "Google Maps did not finish loading. Check the browser API key restrictions and network access.";
          }
        }, 12000);
      }
    } catch (error) {
      notify(error.message, "error");
    }
  }

  function initializeGoogleMapIfReady() {
    if (appState.mapInitialized || !appState.config || !window.google || !window.google.maps) return;
    appState.mapInitialized = true;
    AlduorMap.initMap(appState.config, appState.zones, onGeometryChange);
    if (appState.selectedZone) AlduorMap.applyZone(appState.selectedZone, appState.selectedRadiusMeters);
  }

  function renderControls(config, zones) {
    const zoneSelect = document.getElementById("zone-select");
    zoneSelect.textContent = "";
    zones.forEach((zone) => {
      const option = document.createElement("option");
      option.value = zone.id;
      option.textContent = zone.name;
      zoneSelect.appendChild(option);
    });

    const radiusSelect = document.getElementById("radius-select");
    config.radius_options.forEach((radius) => {
      const option = document.createElement("option");
      option.value = String(radius);
      option.textContent = `${radius / 1000} km`;
      option.selected = radius === 5000;
      radiusSelect.appendChild(option);
    });

    AlduorJobs.initializeProjectTypes(config.project_types, defaultProjectTypes);
    updateGeometryPreview();
  }

  function bindControls() {
    document.getElementById("zone-select").addEventListener("change", (event) => {
      appState.selectedZone = appState.zones.find((zone) => zone.id === event.target.value);
      appState.searchMode = "zone";
      appState.customGeometry = null;
      AlduorMap.clearDrawing(onGeometryChange);
      AlduorMap.applyZone(appState.selectedZone, appState.selectedRadiusMeters);
      updateGeometryPreview();
    });

    document.getElementById("radius-select").addEventListener("change", (event) => {
      appState.selectedRadiusMeters = Number(event.target.value);
      if (appState.selectedZone) AlduorMap.applyZone(appState.selectedZone, appState.selectedRadiusMeters);
      updateGeometryPreview();
    });

    document.getElementById("draw-rectangle").addEventListener("click", () => AlduorMap.startRectangle());
    document.getElementById("draw-polygon").addEventListener("click", () => AlduorMap.startPolygon());
    document.getElementById("clear-drawing").addEventListener("click", () => {
      appState.searchMode = "zone";
      AlduorMap.clearDrawing(onGeometryChange);
      updateGeometryPreview();
    });
    document.getElementById("select-all-types").addEventListener("click", () => AlduorJobs.setAllProjectTypes(true));
    document.getElementById("clear-all-types").addEventListener("click", () => AlduorJobs.setAllProjectTypes(false));
    document.getElementById("refresh-jobs").addEventListener("click", () => AlduorJobs.loadJobs().catch((error) => notify(error.message, "error")));
    document.getElementById("search-form").addEventListener("submit", async (event) => {
      event.preventDefault();
      clearErrors();
      try {
        validateClientSide();
        await AlduorJobs.submitJob(appState);
      } catch (error) {
        showValidation(error.message);
      }
    });
  }

  function onGeometryChange(geometry) {
    appState.customGeometry = geometry;
    if (geometry) appState.searchMode = geometry.type;
    updateGeometryPreview();
  }

  function updateGeometryPreview() {
    const summary = document.getElementById("geometry-summary");
    const json = document.getElementById("geometry-json");
    const geometry = appState.customGeometry;
    if (geometry) {
      const count = geometry.coordinates ? geometry.coordinates.length : 4;
      summary.textContent = `Type: ${geometry.type}. Points: ${count}`;
      json.textContent = JSON.stringify(geometry, null, 2);
      return;
    }
    const zone = appState.selectedZone;
    summary.textContent = `Zone mode: ${zone ? zone.name : "Lahore"}`;
    json.textContent = JSON.stringify({ search_mode: "zone", zone_id: zone ? zone.id : null, radius_meters: appState.selectedRadiusMeters }, null, 2);
  }

  function validateClientSide() {
    if (AlduorJobs.selectedProjectTypes().length === 0) throw new Error("Select at least one project type.");
    if (!appState.customGeometry && !appState.selectedZone) throw new Error("Select a Lahore zone or draw an area.");
    if (appState.customGeometry && !geometryInsideBoundary(appState.customGeometry)) {
      throw new Error("The selected area falls outside the current Lahore service boundary. Please adjust the map selection.");
    }
    if (appState.customGeometry && appState.customGeometry.type === "polygon" && appState.customGeometry.coordinates.length < 3) {
      throw new Error("Polygon must have at least three points.");
    }
  }

  function geometryInsideBoundary(geometry) {
    const b = appState.config.service_boundary;
    const points = geometry.type === "rectangle"
      ? [{ lat: geometry.north, lng: geometry.east }, { lat: geometry.north, lng: geometry.west }, { lat: geometry.south, lng: geometry.east }, { lat: geometry.south, lng: geometry.west }]
      : geometry.coordinates;
    return points.every((point) => point.lat <= b.north && point.lat >= b.south && point.lng <= b.east && point.lng >= b.west);
  }

  function showValidation(message) {
    if (message.includes("project type")) document.getElementById("types-error").textContent = message;
    else if (message.includes("area") || message.includes("Polygon") || message.includes("boundary")) document.getElementById("geometry-error").textContent = message;
    notify(message, "error");
  }

  function clearErrors() {
    document.getElementById("types-error").textContent = "";
    document.getElementById("geometry-error").textContent = "";
    document.getElementById("zone-error").textContent = "";
  }

  function bindModal() {
    const modal = document.getElementById("job-modal");
    document.getElementById("close-job-modal").addEventListener("click", () => modal.close());
    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape" && modal.open) modal.close();
    });
  }

  function notify(message, type) {
    const element = document.getElementById("notification");
    element.textContent = message;
    element.className = `notification is-visible ${type || ""}`;
    window.setTimeout(() => { element.className = "notification"; }, 4500);
  }

  window.AlduorApp = { notify };
  window.gm_authFailure = function () {
    document.getElementById("map-status").textContent = "Google Maps rejected the browser API key. Check key restrictions and Maps JavaScript API access.";
  };
  window.addEventListener("DOMContentLoaded", start);
  window.addEventListener("alduor:google-ready", initializeGoogleMapIfReady);
})();
