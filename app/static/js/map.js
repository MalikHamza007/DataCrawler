(function () {
  const state = {
    map: null,
    drawingManager: null,
    activeShape: null,
    activeInfoWindow: null,
    radiusCircle: null
  };

  function initMap(config, zones, onGeometryChange) {
    const mapStatus = document.getElementById("map-status");
    if (!window.google || !window.google.maps) {
      mapStatus.textContent = "Google Maps could not be loaded. Check the browser API key and network connection.";
      return;
    }
    state.map = new google.maps.Map(document.getElementById("map"), {
      center: config.default_center,
      zoom: config.default_zoom,
      mapTypeControl: false,
      streetViewControl: false,
      fullscreenControl: true
    });
    mapStatus.textContent = "Lahore map ready.";

    state.drawingManager = new google.maps.drawing.DrawingManager({
      drawingControl: false,
      rectangleOptions: shapeOptions(),
      polygonOptions: shapeOptions()
    });
    state.drawingManager.setMap(state.map);
    google.maps.event.addListener(state.drawingManager, "overlaycomplete", (event) => {
      clearShape();
      state.activeShape = event.overlay;
      state.drawingManager.setDrawingMode(null);
      const geometry = extractGeometry(event.type, event.overlay);
      onGeometryChange(geometry);
    });
  }

  function shapeOptions() {
    return {
      strokeColor: "#1f7a8c",
      strokeOpacity: 0.9,
      strokeWeight: 2,
      fillColor: "#1f7a8c",
      fillOpacity: 0.16,
      editable: true,
      draggable: false
    };
  }

  function startRectangle() {
    if (state.drawingManager) state.drawingManager.setDrawingMode(google.maps.drawing.OverlayType.RECTANGLE);
  }

  function startPolygon() {
    if (state.drawingManager) state.drawingManager.setDrawingMode(google.maps.drawing.OverlayType.POLYGON);
  }

  function clearShape() {
    if (state.activeShape) {
      state.activeShape.setMap(null);
      state.activeShape = null;
    }
  }

  function clearDrawing(onGeometryChange) {
    clearShape();
    if (state.drawingManager) state.drawingManager.setDrawingMode(null);
    onGeometryChange(null);
  }

  function extractGeometry(type, shape) {
    if (type === "rectangle") {
      const bounds = shape.getBounds();
      const ne = bounds.getNorthEast();
      const sw = bounds.getSouthWest();
      return { type: "rectangle", north: ne.lat(), south: sw.lat(), east: ne.lng(), west: sw.lng() };
    }
    const coordinates = shape.getPath().getArray().map((point) => ({ lat: point.lat(), lng: point.lng() }));
    return { type: "polygon", coordinates };
  }

  function applyZone(zone, radiusMeters) {
    if (!state.map || !window.google) return;
    if (zone.bounds) {
      state.map.fitBounds({
        north: zone.bounds.north,
        south: zone.bounds.south,
        east: zone.bounds.east,
        west: zone.bounds.west
      });
    } else {
      state.map.setCenter(zone.center);
      state.map.setZoom(zone.zoom);
    }
    showRadius(zone.center, radiusMeters);
  }

  function showRadius(center, radiusMeters) {
    if (!state.map || !window.google) return;
    if (state.radiusCircle) state.radiusCircle.setMap(null);
    state.radiusCircle = new google.maps.Circle({
      map: state.map,
      center,
      radius: radiusMeters,
      strokeColor: "#d7a84b",
      strokeOpacity: 0.75,
      strokeWeight: 2,
      fillColor: "#d7a84b",
      fillOpacity: 0.08
    });
  }

  window.AlduorMap = { initMap, startRectangle, startPolygon, clearDrawing, applyZone };
  window.initAlduorMap = function () {
    window.dispatchEvent(new Event("alduor:google-ready"));
  };
})();
