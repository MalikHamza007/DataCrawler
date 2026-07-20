import { dashboardState } from "./state.js";
import { api } from "./dashboard-api.js";
import { notify } from "./notifications.js";

window.initAlduorDashboardMap = function () {
  window.dispatchEvent(new Event("alduor:dashboard-google-ready"));
};

export function initMap(onSelectProject) {
  const status = document.getElementById("map-status");
  if (!window.ALDUOR_CONFIG.googleMapsConfigured) {
    status.textContent = "Google Maps is not configured.";
    return;
  }
  if (!window.ALDUOR_CONFIG.googleMapsMapId) {
    status.textContent = "Google Map ID is missing. Add GOOGLE_MAPS_MAP_ID to .env.";
    return;
  }
  if (!window.google || !window.google.maps) return;
  if (dashboardState.map) return;
  dashboardState.map = new google.maps.Map(document.getElementById("map"), {
    center: { lat: 31.5204, lng: 74.3587 },
    zoom: 11,
    mapId: window.ALDUOR_CONFIG.googleMapsMapId,
    mapTypeControl: false,
    streetViewControl: false
  });
  dashboardState.infoWindow = new google.maps.InfoWindow();
  status.textContent = "Lahore map ready.";
  dashboardState.map.addListener("idle", () => {
    const bounds = dashboardState.map.getBounds();
    if (!bounds) return;
    const ne = bounds.getNorthEast();
    const sw = bounds.getSouthWest();
    dashboardState.mapBounds = { north: ne.lat(), south: sw.lat(), east: ne.lng(), west: sw.lng(), zoom: dashboardState.map.getZoom() };
  });
  document.getElementById("search-map-area").addEventListener("click", () => loadMapProjects(onSelectProject));
  loadMapProjects(onSelectProject);
  window.dispatchEvent(new Event("alduor:dashboard-map-ready"));
}

export function useVisibleArea(onChange, serviceBoundary) {
  if (!dashboardState.map) return false;
  const bounds = dashboardState.map.getBounds();
  if (!bounds) return false;
  const ne = bounds.getNorthEast();
  const sw = bounds.getSouthWest();
  const geometry = {
    type: "rectangle",
    north: Math.min(ne.lat(), serviceBoundary.north),
    south: Math.max(sw.lat(), serviceBoundary.south),
    east: Math.min(ne.lng(), serviceBoundary.east),
    west: Math.max(sw.lng(), serviceBoundary.west)
  };
  if (geometry.north <= geometry.south || geometry.east <= geometry.west) return false;
  resetCollectionSelection();
  dashboardState.collectionSelectionOverlay = new google.maps.Rectangle({
    map: dashboardState.map,
    bounds: geometry,
    ...selectionStyle()
  });
  dashboardState.collectionGeometry = geometry;
  onChange(geometry);
  return true;
}

export function useNamedArea(bounds, onChange) {
  if (!dashboardState.map || !bounds) return false;
  const geometry = { type: "rectangle", north: bounds.north, south: bounds.south, east: bounds.east, west: bounds.west };
  resetCollectionSelection();
  dashboardState.map.fitBounds(bounds);
  dashboardState.collectionSelectionOverlay = new google.maps.Rectangle({
    map: dashboardState.map,
    bounds: geometry,
    ...selectionStyle()
  });
  dashboardState.collectionGeometry = geometry;
  onChange(geometry);
  return true;
}

export function useRadiusArea(center, radiusMeters, onChange) {
  if (!dashboardState.map || !center) return false;
  resetCollectionSelection();
  setCircleSelection(center, radiusMeters, onChange);
  return true;
}

export function startCircleSelection(radiusMeters, onChange, onProgress) {
  if (!dashboardState.map) return false;
  resetCollectionSelection();
  dashboardState.collectionSelectionMode = "circle";
  onChange(null);
  onProgress(`Click the map center for a ${formatRadius(radiusMeters)} search circle.`);
  dashboardState.collectionSelectionListener = dashboardState.map.addListener("click", (event) => {
    const center = { lat: event.latLng.lat(), lng: event.latLng.lng() };
    stopSelectionListener();
    dashboardState.collectionSelectionMode = null;
    setCircleSelection(center, radiusMeters, onChange);
  });
  return true;
}

export function updateCircleRadius(radiusMeters, onChange) {
  const geometry = dashboardState.collectionGeometry;
  const center = geometry?.type === "radius" && geometry.map_center
    ? geometry.map_center
    : dashboardState.map
      ? { lat: dashboardState.map.getCenter().lat(), lng: dashboardState.map.getCenter().lng() }
      : null;
  if (!center) return false;
  resetCollectionSelection();
  setCircleSelection(center, radiusMeters, onChange);
  return true;
}

export function startRectangleSelection(onChange, onProgress) {
  if (!dashboardState.map) return false;
  resetCollectionSelection();
  dashboardState.collectionSelectionMode = "rectangle";
  onChange(null);
  onProgress("Click the first corner of the rectangle.");
  dashboardState.collectionSelectionListener = dashboardState.map.addListener("click", (event) => {
    const point = { lat: event.latLng.lat(), lng: event.latLng.lng() };
    dashboardState.collectionSelectionPoints.push(point);
    if (dashboardState.collectionSelectionPoints.length === 1) {
      dashboardState.collectionSelectionOverlay = new google.maps.Circle({
        map: dashboardState.map,
        center: point,
        radius: 45,
        ...selectionStyle()
      });
      onProgress("Click the opposite corner to finish the rectangle.");
      return;
    }
    const [first, second] = dashboardState.collectionSelectionPoints;
    const geometry = {
      type: "rectangle",
      north: Math.max(first.lat, second.lat),
      south: Math.min(first.lat, second.lat),
      east: Math.max(first.lng, second.lng),
      west: Math.min(first.lng, second.lng)
    };
    removeSelectionOverlay();
    dashboardState.collectionSelectionOverlay = new google.maps.Rectangle({
      map: dashboardState.map,
      bounds: geometry,
      ...selectionStyle()
    });
    stopSelectionListener();
    dashboardState.collectionSelectionMode = null;
    dashboardState.collectionGeometry = geometry;
    onChange(geometry);
  });
  return true;
}

export function startPolygonSelection(onChange, onProgress) {
  if (!dashboardState.map) return false;
  resetCollectionSelection();
  dashboardState.collectionSelectionMode = "polygon";
  dashboardState.collectionSelectionOverlay = new google.maps.Polygon({
    map: dashboardState.map,
    paths: [],
    ...selectionStyle()
  });
  onChange(null);
  onProgress("Click at least three points, then choose Finish Polygon.");
  dashboardState.collectionSelectionListener = dashboardState.map.addListener("click", (event) => {
    if (dashboardState.collectionSelectionPoints.length >= 100) return;
    dashboardState.collectionSelectionPoints.push({ lat: event.latLng.lat(), lng: event.latLng.lng() });
    dashboardState.collectionSelectionOverlay.setPath(dashboardState.collectionSelectionPoints);
    onProgress(`${dashboardState.collectionSelectionPoints.length} polygon point${dashboardState.collectionSelectionPoints.length === 1 ? "" : "s"} selected.`);
  });
  return true;
}

export function finishPolygonSelection(onChange) {
  if (dashboardState.collectionSelectionMode !== "polygon" || dashboardState.collectionSelectionPoints.length < 3) return false;
  const geometry = { type: "polygon", coordinates: dashboardState.collectionSelectionPoints.map((point) => ({ ...point })) };
  stopSelectionListener();
  dashboardState.collectionSelectionMode = null;
  dashboardState.collectionGeometry = geometry;
  onChange(geometry);
  return true;
}

export function clearCollectionSelection(onChange) {
  resetCollectionSelection();
  onChange(null);
}

export async function loadMapProjects(onSelectProject) {
  if (!dashboardState.mapBounds) dashboardState.mapBounds = { north: 31.75, south: 31.35, east: 74.55, west: 74.15, zoom: 11 };
  try {
    const data = await api.mapProjects({ ...dashboardState.filters, ...dashboardState.mapBounds, limit: 1000 });
    renderMarkers(data.items, onSelectProject);
    const warning = document.getElementById("map-warning");
    warning.hidden = !data.truncated;
    warning.textContent = data.truncated ? `Showing ${data.returned} of ${data.total_matching} matching projects. Zoom in or apply filters.` : "";
  } catch (error) {
    if (error.name === "AbortError") return;
    notify(`Map data could not be loaded. ${error.message}`);
  }
}

function renderMarkers(items, onSelectProject) {
  clearMarkers();
  if (!dashboardState.map || !window.google?.maps?.marker?.AdvancedMarkerElement) return;
  items.forEach((item) => {
    const glyph = glyphFor(item);
    const pin = document.createElement("div");
    pin.className = "badge";
    pin.textContent = glyph;
    pin.setAttribute("aria-label", `${item.name} ${item.review_status}`);
    const marker = new google.maps.marker.AdvancedMarkerElement({
      map: dashboardState.map,
      position: { lat: item.latitude, lng: item.longitude },
      title: `${glyph} ${item.name}`,
      content: pin
    });
    marker.addListener("click", () => {
      onSelectProject(item.id, { openDrawer: false });
      openInfo(item, marker);
    });
    dashboardState.projectMarkers.set(item.id, marker);
  });
  if (window.markerClusterer?.MarkerClusterer) {
    dashboardState.markerClusterer = new window.markerClusterer.MarkerClusterer({ map: dashboardState.map, markers: Array.from(dashboardState.projectMarkers.values()) });
  }
}

function openInfo(item, marker) {
  const container = document.createElement("div");
  const title = document.createElement("strong");
  title.textContent = item.name;
  const meta = document.createElement("p");
  meta.textContent = `${item.developer ? item.developer.name : "Unassigned"} | ${item.project_type || "Unknown"} | ${item.review_status}`;
  const button = document.createElement("button");
  button.type = "button";
  button.textContent = "Open Project";
  button.addEventListener("click", () => document.dispatchEvent(new CustomEvent("alduor:open-project", { detail: { id: item.id } })));
  container.append(title, meta, button);
  dashboardState.infoWindow.setContent(container);
  dashboardState.infoWindow.open({ map: dashboardState.map, anchor: marker });
}

export function selectMarker(project) {
  const marker = dashboardState.projectMarkers.get(project.id);
  if (marker && dashboardState.map) {
    dashboardState.map.panTo(marker.position);
  }
}

function glyphFor(item) {
  if (item.review_status === "approved") return "✓";
  if (item.review_status === "needs_review") return "!";
  if (["rejected", "excluded"].includes(item.review_status)) return "x";
  return "?";
}

function setCircleSelection(center, radiusMeters, onChange) {
  removeSelectionOverlay();
  dashboardState.collectionSelectionOverlay = new google.maps.Circle({
    map: dashboardState.map,
    center,
    radius: radiusMeters,
    ...selectionStyle()
  });
  dashboardState.collectionGeometry = {
    type: "radius",
    map_center: center,
    radius_meters: radiusMeters
  };
  if (dashboardState.map) {
    const bounds = dashboardState.collectionSelectionOverlay.getBounds();
    if (bounds) dashboardState.map.fitBounds(bounds);
  }
  onChange(dashboardState.collectionGeometry);
}

function formatRadius(radiusMeters) {
  return `${Math.round(radiusMeters / 1000)} km`;
}

function clearMarkers() {
  if (dashboardState.markerClusterer) dashboardState.markerClusterer.clearMarkers();
  dashboardState.projectMarkers.forEach((marker) => { marker.map = null; });
  dashboardState.projectMarkers.clear();
}

function selectionStyle() {
  return {
    strokeColor: "#1f7a8c",
    strokeOpacity: 0.95,
    strokeWeight: 2,
    fillColor: "#1f7a8c",
    fillOpacity: 0.16,
    clickable: false
  };
}

function resetCollectionSelection() {
  stopSelectionListener();
  removeSelectionOverlay();
  dashboardState.collectionSelectionMode = null;
  dashboardState.collectionSelectionPoints = [];
  dashboardState.collectionGeometry = null;
}

function stopSelectionListener() {
  if (dashboardState.collectionSelectionListener) dashboardState.collectionSelectionListener.remove();
  dashboardState.collectionSelectionListener = null;
}

function removeSelectionOverlay() {
  if (dashboardState.collectionSelectionOverlay) dashboardState.collectionSelectionOverlay.setMap(null);
  dashboardState.collectionSelectionOverlay = null;
}
