const state = {
  dataFile: null,
  kmzFile: null,
  pdfDataFile: null,
  reviewFile: null,
  reviewQueue: [],
  reviewSecondaryQueue: [],
  reviewDecisions: {},
  reviewDraftPlacements: {},
  showSecondaryReview: false,
  currentReviewIndex: 0,
  reviewMapData: null,
  reviewMapPickMode: false,
  reviewMap: null,
  reviewMapLayers: null,
  reviewMapFocusKey: null,
  runId: null,
  logSeq: 0,
  logLines: [],
  pollTimer: null,
  logWindow: null,
  mapReportName: null,
  previewTimer: null,
  previewRequestId: 0,
};

const el = {
  dataDrop: document.getElementById("data-drop"),
  dataInput: document.getElementById("data-input"),
  dataLabel: document.getElementById("data-label"),
  dataHint: document.getElementById("data-hint"),
  kmzDrop: document.getElementById("kmz-drop"),
  kmzInput: document.getElementById("kmz-input"),
  kmzLabel: document.getElementById("kmz-label"),
  kmzHint: document.getElementById("kmz-hint"),
  pdfDrop: document.getElementById("pdf-drop"),
  pdfInput: document.getElementById("pdf-input"),
  pdfLabel: document.getElementById("pdf-label"),
  pdfHint: document.getElementById("pdf-hint"),
  reviewDrop: document.getElementById("review-drop"),
  reviewInput: document.getElementById("review-input"),
  reviewLabel: document.getElementById("review-label"),
  reviewHint: document.getElementById("review-hint"),
  latColumn: document.getElementById("lat-column"),
  lonColumn: document.getElementById("lon-column"),
  labelOrder: document.getElementById("label-order"),
  columnOptions: document.getElementById("column-options"),
  columnHint: document.getElementById("column-hint"),
  generateReport: document.getElementById("generate-report"),
  applyReview: document.getElementById("apply-review"),
  reportProgress: document.getElementById("report-progress"),
  progressBar: document.getElementById("progress-bar"),
  statusBar: document.getElementById("status-bar"),
  statusTitle: document.getElementById("status-title"),
  statusDetail: document.getElementById("status-detail"),
  runRefine: document.getElementById("run-refine"),
  clearSession: document.getElementById("clear-session"),
  summaryData: document.getElementById("summary-data"),
  summaryKmz: document.getElementById("summary-kmz"),
  summaryColumns: document.getElementById("summary-columns"),
  runLog: document.getElementById("run-log"),
  popLog: document.getElementById("pop-log"),
  snapshotTag: document.getElementById("snapshot-tag"),
  snapshotStatus: document.getElementById("snapshot-status"),
  snapshotLastRun: document.getElementById("snapshot-last-run"),
  metrics: document.getElementById("metrics"),
  outputLinks: document.getElementById("output-links"),
  mapFrame: document.getElementById("map-frame"),
  mapPlaceholder: document.getElementById("map-placeholder"),
  mapSubtitle: document.getElementById("map-subtitle"),
  mapMode: document.getElementById("map-mode"),
  wizardMap: document.getElementById("wizard-map"),
  wizardMapToolbar: document.getElementById("wizard-map-toolbar"),
  wizardMapSelection: document.getElementById("wizard-map-selection"),
  clearMapSelection: document.getElementById("clear-map-selection"),
  openMap: document.getElementById("open-map"),
  reviewList: document.getElementById("review-list"),
  reviewSummary: document.getElementById("review-summary"),
  reviewQueueSubtitle: document.getElementById("review-queue-subtitle"),
  applyBrowserReview: document.getElementById("apply-browser-review"),
  guideModal: document.getElementById("guide-modal"),
  notesModal: document.getElementById("notes-modal"),
  openGuide: document.getElementById("open-guide"),
  openNotes: document.getElementById("open-notes"),
  toast: document.getElementById("toast"),
};

function showToast(message) {
  el.toast.textContent = message;
  el.toast.classList.add("show");
  window.setTimeout(() => el.toast.classList.remove("show"), 3200);
}

function setStatus(stateName, title, detail) {
  el.statusBar.dataset.state = stateName;
  el.statusTitle.textContent = title;
  el.statusDetail.textContent = detail;
}

function setProgressRunning(isRunning) {
  el.progressBar.parentElement.classList.toggle("running", isRunning);
}

function setReportProgressRunning(isRunning) {
  if (!el.reportProgress) return;
  el.reportProgress.classList.toggle("running", isRunning);
}

function updateRunButton() {
  const hasData = !!state.dataFile;
  const hasKmz = !!state.kmzFile;
  const lat = el.latColumn.value.trim();
  const lon = el.lonColumn.value.trim();
  el.runRefine.disabled = !(hasData && hasKmz && lat && lon);
  updateReportButton();
  updateReviewButton();
}

function updateReportButton() {
  const hasSource = !!state.pdfDataFile || !!state.runId || !!state.dataFile;
  el.generateReport.disabled = !hasSource;
}

function updateReviewButton() {
  const hasSourceRun = !!state.runId;
  const hasReviewFile = !!state.reviewFile;
  el.applyReview.disabled = !(hasSourceRun && hasReviewFile);
  updateBrowserReviewButton();
}

function updateBrowserReviewButton() {
  const selectedCount = Object.keys(state.reviewDecisions).length;
  el.applyBrowserReview.disabled = !(state.runId && selectedCount > 0);
}

function updateSummary() {
  el.summaryData.textContent = state.dataFile ? state.dataFile.name : "No file selected.";
  el.summaryKmz.textContent = state.kmzFile ? state.kmzFile.name : "No boundary selected.";
  const lat = el.latColumn.value.trim();
  const lon = el.lonColumn.value.trim();
  el.summaryColumns.textContent = lat && lon ? `${lat} / ${lon}` : "Latitude / Longitude not set.";
}

function updateColumnOptions(headers) {
  el.columnOptions.innerHTML = "";
  headers.forEach((header) => {
    const option = document.createElement("option");
    option.value = header;
    el.columnOptions.appendChild(option);
  });
}

async function fetchHeaders(file) {
  const form = new FormData();
  form.append("data_file", file);
  el.columnHint.textContent = "Detecting columns...";
  const response = await fetch("/api/preview", { method: "POST", body: form });
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    el.columnHint.textContent = data.error || "Unable to detect columns.";
    return;
  }
  const data = await response.json();
  const headers = data.headers || [];
  if (headers.length) {
    updateColumnOptions(headers);
    el.columnHint.textContent = `${headers.length} columns detected.`;
  } else {
    el.columnHint.textContent = "No headers detected. Type columns manually.";
  }
  if (data.latGuess && !el.latColumn.value.trim()) {
    el.latColumn.value = data.latGuess;
  }
  if (data.lonGuess && !el.lonColumn.value.trim()) {
    el.lonColumn.value = data.lonGuess;
  }
  updateSummary();
  updateRunButton();
  schedulePreviewMap();
}

function appendLog(entries) {
  if (!entries || !entries.length) return;
  entries.forEach((entry) => {
    const line = document.createElement("div");
    line.className = `log-line ${entry.level || "info"}`;
    line.textContent = entry.text;
    el.runLog.appendChild(line);
    state.logLines.push(entry.text);
  });
  while (state.logLines.length > 400) {
    state.logLines.shift();
    el.runLog.removeChild(el.runLog.firstChild);
  }
  el.runLog.scrollTop = el.runLog.scrollHeight;
  syncLogWindow();
}

function clearLogs() {
  state.logLines = [];
  el.runLog.innerHTML = "";
  syncLogWindow();
}

function renderMetrics(summary) {
  el.metrics.innerHTML = "";
  if (!summary || !summary.metrics) return;
  summary.metrics.forEach((metric) => {
    const card = document.createElement("div");
    card.className = "metric";
    card.innerHTML = `
      <div class="metric-label">${metric.label}</div>
      <div class="metric-value">${metric.value}</div>
      <div class="metric-detail">${metric.detail || ""}</div>
    `;
    el.metrics.appendChild(card);
  });
}

function renderOutputs(outputs) {
  if (!outputs || outputs.length === 0) {
    el.outputLinks.textContent = "No outputs yet.";
    return;
  }
  el.outputLinks.innerHTML = "";
  outputs.forEach((item) => {
    const link = document.createElement("a");
    link.href = `/api/run/${state.runId}/download/${encodeURIComponent(item.name)}`;
    link.textContent = item.name;
    link.target = "_blank";
    el.outputLinks.appendChild(link);
  });
}

function setMapPreview(mapName, mapUrl) {
  state.mapReportName = mapName;
  const url = mapUrl || (mapName ? `/api/run/${state.runId}/view/${encodeURIComponent(mapName)}` : null);
  if (!url) {
    el.mapFrame.removeAttribute("src");
    el.mapPlaceholder.style.display = "flex";
    el.openMap.disabled = true;
    return;
  }
  el.mapFrame.src = url;
  el.mapPlaceholder.style.display = "none";
  el.openMap.disabled = false;
  el.openMap.dataset.url = url;
}

function schedulePreviewMap() {
  if (!state.dataFile || !state.kmzFile || state.pollTimer) return;
  if (state.previewTimer) {
    window.clearTimeout(state.previewTimer);
  }
  state.previewTimer = window.setTimeout(requestPreviewMap, 300);
}

async function requestPreviewMap() {
  if (!state.dataFile || !state.kmzFile || state.pollTimer) return;
  const requestId = ++state.previewRequestId;
  el.mapPlaceholder.textContent = "Loading map preview...";
  el.mapPlaceholder.style.display = "flex";
  el.openMap.disabled = true;

  const form = new FormData();
  form.append("data_file", state.dataFile);
  form.append("boundary_file", state.kmzFile);
  form.append("lat_column", el.latColumn.value.trim());
  form.append("lon_column", el.lonColumn.value.trim());

  const response = await fetch("/api/preview-map", { method: "POST", body: form });
  if (requestId !== state.previewRequestId) return;
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    el.mapPlaceholder.textContent = data.error || "Map preview unavailable.";
    el.mapPlaceholder.style.display = "flex";
    setMapPreview(null);
    return;
  }
  const data = await response.json().catch(() => ({}));
  if (data.latGuess && !el.latColumn.value.trim()) {
    el.latColumn.value = data.latGuess;
  }
  if (data.lonGuess && !el.lonColumn.value.trim()) {
    el.lonColumn.value = data.lonGuess;
  }
  if (data.previewUrl) {
    setMapPreview(null, data.previewUrl);
  }
  updateSummary();
  updateRunButton();
}

function buildRunFormData() {
  const form = new FormData();
  form.append("data_file", state.dataFile);
  form.append("boundary_file", state.kmzFile);
  form.append("lat_column", el.latColumn.value.trim());
  form.append("lon_column", el.lonColumn.value.trim());
  form.append("label_order", el.labelOrder.value);
  return form;
}

function buildReportFormData() {
  const form = new FormData();
  form.append("lat_column", el.latColumn.value.trim());
  form.append("lon_column", el.lonColumn.value.trim());
  if (state.pdfDataFile) {
    form.append("pdf_data_file", state.pdfDataFile);
  } else if (state.runId) {
    form.append("source_run_id", state.runId);
  } else if (state.dataFile) {
    form.append("data_file", state.dataFile);
  }
  return form;
}

function buildReviewFormData() {
  const form = new FormData();
  form.append("source_run_id", state.runId);
  form.append("coordinate_review_file", state.reviewFile);
  form.append("lat_column", el.latColumn.value.trim());
  form.append("lon_column", el.lonColumn.value.trim());
  form.append("label_order", el.labelOrder.value);
  return form;
}

function buildBrowserReviewFormData() {
  const form = new FormData();
  form.append("source_run_id", state.runId);
  form.append("lat_column", el.latColumn.value.trim());
  form.append("lon_column", el.lonColumn.value.trim());
  form.append("label_order", el.labelOrder.value);
  form.append("review_decisions", JSON.stringify(Object.values(state.reviewDecisions)));
  return form;
}

function formatCoordinate(value) {
  const numeric = Number(value);
  return Number.isFinite(numeric) ? numeric.toFixed(6) : "--";
}

function getVisibleReviewSteps() {
  if (state.showSecondaryReview) {
    return [...state.reviewQueue, ...state.reviewSecondaryQueue];
  }
  return [...state.reviewQueue];
}

function clampReviewIndex() {
  const visibleSteps = getVisibleReviewSteps();
  if (!visibleSteps.length) {
    state.currentReviewIndex = 0;
    return null;
  }
  if (state.currentReviewIndex < 0) {
    state.currentReviewIndex = 0;
  }
  if (state.currentReviewIndex >= visibleSteps.length) {
    state.currentReviewIndex = visibleSteps.length - 1;
  }
  return visibleSteps[state.currentReviewIndex];
}

function getCurrentReviewStep() {
  return clampReviewIndex();
}

function getAllReviewSteps() {
  return [...state.reviewQueue, ...state.reviewSecondaryQueue];
}

function findReviewStep(rowKey) {
  return getAllReviewSteps().find((step) => step.rowKey === rowKey) || null;
}

function focusReviewStep(rowKey) {
  let visibleSteps = getVisibleReviewSteps();
  let index = visibleSteps.findIndex((step) => step.rowKey === rowKey);
  if (index >= 0) {
    state.currentReviewIndex = index;
    return;
  }

  const secondaryIndex = state.reviewSecondaryQueue.findIndex((step) => step.rowKey === rowKey);
  if (secondaryIndex >= 0 && !state.showSecondaryReview) {
    state.showSecondaryReview = true;
    visibleSteps = getVisibleReviewSteps();
    index = visibleSteps.findIndex((step) => step.rowKey === rowKey);
    if (index >= 0) {
      state.currentReviewIndex = index;
    }
  }
}

function getDraftPlacement(step) {
  if (!step) return null;
  return state.reviewDraftPlacements[step.rowKey] || null;
}

function getDecisionPlacement(step) {
  if (!step) return null;
  const decision = state.reviewDecisions[step.rowKey];
  if (!decision || decision.action !== "apply") return null;
  return {
    latitude: decision.latitude,
    longitude: decision.longitude,
    placementMode: decision.placementMode || "suggested",
  };
}

function countReviewDecisions() {
  const stats = {
    suggested: 0,
    manual: 0,
    rejected: 0,
  };
  Object.values(state.reviewDecisions).forEach((decision) => {
    if (decision.action === "reject") {
      stats.rejected += 1;
      return;
    }
    if (decision.placementMode === "manual") {
      stats.manual += 1;
      return;
    }
    stats.suggested += 1;
  });
  return stats;
}

function pointInRing(point, ring) {
  const [lat, lon] = point;
  let inside = false;
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    const [ilat, ilon] = ring[i];
    const [jlat, jlon] = ring[j];
    const intersects = ((ilat > lat) !== (jlat > lat))
      && (lon < ((jlon - ilon) * (lat - ilat)) / ((jlat - ilat) || Number.EPSILON) + ilon);
    if (intersects) {
      inside = !inside;
    }
  }
  return inside;
}

function pointInProjectBoundary(latitude, longitude) {
  const polygon = state.reviewMapData && Array.isArray(state.reviewMapData.polygon)
    ? state.reviewMapData.polygon
    : [];
  if (!polygon.length) return true;
  if (!pointInRing([latitude, longitude], polygon[0])) {
    return false;
  }
  for (let index = 1; index < polygon.length; index += 1) {
    if (pointInRing([latitude, longitude], polygon[index])) {
      return false;
    }
  }
  return true;
}

function resetReviewMap() {
  if (!state.reviewMap) return;
  try {
    state.reviewMap.off();
    state.reviewMap.remove();
  } catch (error) {
    console.error("Review map reset failed.", error);
  }
  state.reviewMap = null;
  state.reviewMapLayers = null;
  state.reviewMapFocusKey = null;
}

function ensureReviewMap() {
  if (state.reviewMap || !window.L) return;

  state.reviewMap = window.L.map(el.wizardMap, {
    zoomControl: true,
    attributionControl: true,
  });

  const imagery = window.L.tileLayer(
    "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
    {
      maxZoom: 19,
      attribution: "Tiles (c) Esri",
    }
  );
  const streets = window.L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19,
    attribution: "&copy; OpenStreetMap contributors",
  });

  imagery.addTo(state.reviewMap);
  state.reviewMapLayers = {
    imagery,
    streets,
    boundary: null,
    context: window.L.layerGroup().addTo(state.reviewMap),
    suggested: window.L.layerGroup().addTo(state.reviewMap),
    selected: window.L.layerGroup().addTo(state.reviewMap),
  };
  window.L.control.layers(
    {
      Imagery: imagery,
      Streets: streets,
    },
    {
      "Refined crashes": state.reviewMapLayers.context,
      "Review markers": state.reviewMapLayers.selected,
    }
  ).addTo(state.reviewMap);

  state.reviewMap.on("click", (event) => {
    const current = getCurrentReviewStep();
    if (!current || !state.reviewMapPickMode) return;
    state.reviewDraftPlacements[current.rowKey] = {
      latitude: Number(event.latlng.lat.toFixed(6)),
      longitude: Number(event.latlng.lng.toFixed(6)),
    };
    state.reviewMapPickMode = false;
    renderReviewQueue();
  });
}

function showProjectPreviewMap() {
  el.mapMode.textContent = "Project Map";
  el.mapSubtitle.textContent = "Project map preview and crash placement canvas.";
  el.wizardMap.hidden = true;
  el.mapFrame.style.display = "block";
  el.wizardMapToolbar.hidden = true;
  el.clearMapSelection.disabled = true;
  if (el.mapFrame.getAttribute("src")) {
    el.mapPlaceholder.style.display = "none";
  } else {
    el.mapPlaceholder.style.display = "flex";
  }
}

function renderReviewMap() {
  const current = getCurrentReviewStep();
  if (!current || !state.reviewMapData || !window.L) {
    showProjectPreviewMap();
    return;
  }

  const drawMap = () => {
    el.mapMode.textContent = "Review Wizard";
    el.mapSubtitle.textContent = `Inspect crash ${state.currentReviewIndex + 1} of ${getVisibleReviewSteps().length} and place it on the map if needed.`;
    el.mapFrame.style.display = "none";
    el.wizardMap.hidden = false;
    el.mapPlaceholder.style.display = "none";
    el.wizardMapToolbar.hidden = false;

    ensureReviewMap();
    if (!state.reviewMap || !state.reviewMapLayers) {
      showProjectPreviewMap();
      return;
    }

    window.setTimeout(() => {
      try {
        if (state.reviewMap) {
          state.reviewMap.invalidateSize();
        }
      } catch (error) {
        console.error("Review map resize failed.", error);
      }
    }, 0);

    const polygon = state.reviewMapData.polygon || [];
    const contextPoints = state.reviewMapData.points || [];
    const { context, suggested, selected } = state.reviewMapLayers;
    const draftPlacement = getDraftPlacement(current);
    const decisionPlacement = getDecisionPlacement(current);
    const activePlacement = draftPlacement || decisionPlacement;
    const boundaryBounds = polygon.length && polygon[0].length
      ? window.L.latLngBounds(polygon[0])
      : null;

    if (!state.reviewMap._loaded) {
      if (activePlacement) {
        state.reviewMap.setView([activePlacement.latitude, activePlacement.longitude], 17);
      } else if (current.hasSuggestion) {
        state.reviewMap.setView([current.suggestedLatitude, current.suggestedLongitude], 17);
      } else if (boundaryBounds) {
        state.reviewMap.fitBounds(boundaryBounds, { padding: [20, 20] });
      } else {
        state.reviewMap.setView([39.5, -86.0], 7);
      }
    }

    if (state.reviewMapLayers.boundary) {
      state.reviewMap.removeLayer(state.reviewMapLayers.boundary);
    }
    state.reviewMapLayers.boundary = window.L.polygon(polygon, {
      color: "#58a6ff",
      weight: 3,
      fillColor: "#0c2d50",
      fillOpacity: 0.18,
    }).addTo(state.reviewMap);

    context.clearLayers();
    suggested.clearLayers();
    selected.clearLayers();

    contextPoints.forEach((point) => {
      window.L.circleMarker(point, {
        radius: 3,
        color: "#2ea043",
        fillColor: "#2ea043",
        fillOpacity: 0.7,
        weight: 1,
      }).addTo(context);
    });

    if (current.hasSuggestion) {
      window.L.circleMarker([current.suggestedLatitude, current.suggestedLongitude], {
        radius: 8,
        color: "#f59e0b",
        fillColor: "#f59e0b",
        fillOpacity: 0.85,
        weight: 2,
      }).bindTooltip("Suggested placement", { direction: "top" }).addTo(suggested);
    }
    if (activePlacement) {
      const isInside = pointInProjectBoundary(activePlacement.latitude, activePlacement.longitude);
      window.L.circleMarker([activePlacement.latitude, activePlacement.longitude], {
        radius: 8,
        color: isInside ? "#22d3ee" : "#ff3b3b",
        fillColor: isInside ? "#22d3ee" : "#ff3b3b",
        fillOpacity: 0.9,
        weight: 2,
      }).bindTooltip(
        draftPlacement
          ? (isInside ? "Staged placement" : "Staged placement outside boundary")
          : "Confirmed placement",
        { direction: "top" }
      ).addTo(selected);
    }

    if (state.reviewMapFocusKey !== current.rowKey) {
      if (activePlacement) {
        state.reviewMap.setView([activePlacement.latitude, activePlacement.longitude], 17);
      } else if (current.hasSuggestion) {
        state.reviewMap.setView([current.suggestedLatitude, current.suggestedLongitude], 17);
      } else if (boundaryBounds) {
        state.reviewMap.fitBounds(boundaryBounds, { padding: [20, 20] });
      }
      state.reviewMapFocusKey = current.rowKey;
    }

    const decision = state.reviewDecisions[current.rowKey];
    const insideDraft = draftPlacement
      ? pointInProjectBoundary(draftPlacement.latitude, draftPlacement.longitude)
      : false;
    if (state.reviewMapPickMode) {
      el.wizardMapSelection.textContent = `Pick mode is active for crash ${current.crashId}. Click inside the KMZ boundary to stage a custom placement.`;
    } else if (draftPlacement) {
      el.wizardMapSelection.textContent = insideDraft
        ? `Staged custom placement: ${formatCoordinate(draftPlacement.latitude)}, ${formatCoordinate(draftPlacement.longitude)}. Confirm it in the wizard when ready.`
        : `Staged custom placement is outside the KMZ boundary. Pick a point inside the boundary or reject this crash.`;
    } else if (decision && decision.action === "reject") {
      el.wizardMapSelection.textContent = "This crash is marked for rejection and will stay out of the refined data.";
    } else if (decision && decision.action === "apply" && decision.placementMode === "manual") {
      el.wizardMapSelection.textContent = `Manual placement confirmed at ${formatCoordinate(decision.latitude)}, ${formatCoordinate(decision.longitude)}.`;
    } else if (decision && decision.action === "apply") {
      el.wizardMapSelection.textContent = `Suggested placement confirmed at ${formatCoordinate(decision.latitude)}, ${formatCoordinate(decision.longitude)}.`;
    } else if (current.hasSuggestion) {
      el.wizardMapSelection.textContent = "Amber marker shows the suggested placement. Use it, pick a custom point, or reject the crash.";
    } else {
      el.wizardMapSelection.textContent = "No suggested placement was available. Use Pick on Map to stage a location or reject the crash.";
    }
    el.clearMapSelection.disabled = !draftPlacement;
  };

  try {
    drawMap();
  } catch (error) {
    console.error("Review map render failed.", error);
    resetReviewMap();
    try {
      drawMap();
    } catch (retryError) {
      console.error("Review map render retry failed.", retryError);
      showProjectPreviewMap();
    }
  }
}

function moveToNextReviewStep(preferUndecided = false) {
  const visibleSteps = getVisibleReviewSteps();
  if (!visibleSteps.length) return;

  if (preferUndecided) {
    for (let index = state.currentReviewIndex + 1; index < visibleSteps.length; index += 1) {
      if (!state.reviewDecisions[visibleSteps[index].rowKey]) {
        state.currentReviewIndex = index;
        return;
      }
    }
    for (let index = 0; index < visibleSteps.length; index += 1) {
      if (!state.reviewDecisions[visibleSteps[index].rowKey]) {
        state.currentReviewIndex = index;
        return;
      }
    }
  }

  state.currentReviewIndex = Math.min(state.currentReviewIndex + 1, visibleSteps.length - 1);
}

function moveToPreviousReviewStep() {
  const visibleSteps = getVisibleReviewSteps();
  if (!visibleSteps.length) return;
  state.currentReviewIndex = Math.max(state.currentReviewIndex - 1, 0);
}

function describeCurrentDecision(step) {
  if (!step) return "No decision selected yet.";
  const decision = state.reviewDecisions[step.rowKey];
  if (!decision) return "No decision selected yet.";
  if (decision.action === "reject") {
    return "Rejected. This crash will stay out of the refined data set.";
  }
  const label = decision.placementMode === "manual"
    ? "Manual map placement confirmed"
    : "Suggested placement confirmed";
  return `${label}: ${formatCoordinate(decision.latitude)}, ${formatCoordinate(decision.longitude)}.`;
}

function renderReviewQueue() {
  const primarySteps = state.reviewQueue || [];
  const secondarySteps = state.reviewSecondaryQueue || [];
  const visibleSteps = getVisibleReviewSteps();
  const stats = countReviewDecisions();
  const totalLoaded = primarySteps.length + secondarySteps.length;

  el.reviewQueueSubtitle.textContent = totalLoaded
    ? "Step through likely crashes from strongest match to weakest, confirm or place each one on the map, and reject anything that does not belong in the project."
    : "Run refinement to populate the crash placement wizard.";

  if (!totalLoaded) {
    state.showSecondaryReview = false;
    state.currentReviewIndex = 0;
    state.reviewMapPickMode = false;
    el.reviewSummary.textContent = "No likely crash-review items loaded yet.";
    el.reviewList.className = "review-list empty";
    el.reviewList.textContent = state.runId
      ? "This run does not currently need browser review."
      : "Run refinement to populate the crash placement wizard.";
    renderReviewMap();
    updateBrowserReviewButton();
    return;
  }

  const hiddenSecondaryText = secondarySteps.length && !state.showSecondaryReview
    ? `${secondarySteps.length} lower-likelihood crash(es) remain excluded from the wizard for now.`
    : "";
  const pendingVisible = visibleSteps.filter((step) => !state.reviewDecisions[step.rowKey]).length;
  el.reviewSummary.textContent = `${visibleSteps.length} crash(es) in the current wizard pass. ${stats.suggested} suggested confirmed, ${stats.manual} placed on the map, ${stats.rejected} rejected, ${pendingVisible} undecided. ${hiddenSecondaryText}`.trim();

  el.reviewList.className = "review-list wizard-mode";
  el.reviewList.innerHTML = "";

  if (!visibleSteps.length) {
    el.reviewList.innerHTML = `
      <section class="wizard-empty">
        <div class="review-section-title">No Likely Crashes In The Wizard</div>
        <div class="review-section-subtitle">All likely crashes have been filtered out or there are only lower-likelihood candidates available.</div>
        ${secondarySteps.length ? `<button class="btn secondary small" data-action="toggle-secondary">Load Lower-Likelihood Crashes</button>` : ""}
      </section>
    `;
    renderReviewMap();
    updateBrowserReviewButton();
    return;
  }

  const current = getCurrentReviewStep();
  if (!current) {
    renderReviewMap();
    updateBrowserReviewButton();
    return;
  }

  const decision = state.reviewDecisions[current.rowKey];
  const reviewBucket = current.reviewBucket === "secondary" ? "secondary" : "primary";
  const bucketLabel = reviewBucket === "secondary" ? "Secondary" : "Likely";
  const reviewDetails = Array.isArray(current.reviewDetails)
    ? current.reviewDetails.filter((line) => String(line || "").trim())
    : [];
  const metadata = [
    current.crashId ? `Crash ID ${current.crashId}` : "",
    current.crashDate ? `Date ${current.crashDate}` : "",
    current.crashTime ? `Time ${current.crashTime}` : "",
    current.sourceRow ? `Source row ${current.sourceRow}` : "",
    current.groupSize > 1 ? `${current.groupSize} unresolved crash(es) share this pattern` : "",
  ].filter(Boolean);
  const draftPlacement = getDraftPlacement(current);
  const draftInside = draftPlacement
    ? pointInProjectBoundary(draftPlacement.latitude, draftPlacement.longitude)
    : false;
  const canAcceptSuggested = current.hasSuggestion && current.suggestedInsideBoundary !== false;
  const navigationSecondaryLabel = secondarySteps.length
    ? (state.showSecondaryReview ? "Hide Lower-Likelihood Crashes" : "Load Lower-Likelihood Crashes")
    : "";

  el.reviewList.innerHTML = `
    <section class="wizard-card ${decision ? "selected" : ""}">
      <div class="wizard-progress">
        <div class="wizard-step-index">Crash ${state.currentReviewIndex + 1} of ${visibleSteps.length}</div>
        <div class="wizard-step-meta">${escapeHtml(metadata.join(" | ") || "No additional crash metadata available.")}</div>
      </div>
      <div class="review-head">
        <div>
          <div class="review-title">${escapeHtml(current.title)}</div>
          <div class="review-detail">${escapeHtml(current.detail || "Location details unavailable.")}</div>
        </div>
        <div class="review-badges">
          <span class="review-badge ${reviewBucket}">${escapeHtml(bucketLabel)}</span>
          <span class="review-badge">${escapeHtml(current.confidence || "none")}</span>
          <span class="review-badge muted">${escapeHtml((current.method || "manual").replaceAll("_", " "))}</span>
          <span class="review-badge muted">Score ${escapeHtml(String(current.reviewScore ?? 0))}</span>
        </div>
      </div>
      <div class="review-relevance">
        <div class="review-relevance-summary">${escapeHtml(current.reviewReason || "No project-relevance signal was recorded for this crash.")}</div>
        ${
          reviewDetails.length
            ? `
              <ul class="review-relevance-list">
                ${reviewDetails.map((line) => `<li>${escapeHtml(line)}</li>`).join("")}
              </ul>
            `
            : ""
        }
      </div>
      <div class="review-note">${escapeHtml(current.note || "No additional recovery note was recorded for this crash.")}</div>
      ${
        current.hasNarrative
          ? `
            <details class="wizard-narrative">
              <summary>Show Narrative</summary>
              <div class="wizard-narrative-text">${escapeHtmlWithBreaks(current.narrative)}</div>
            </details>
          `
          : ""
      }
      <div class="wizard-suggestion">
        <div class="wizard-suggestion-title">Suggested Placement</div>
        <div class="wizard-suggestion-body">
          ${
            current.hasSuggestion
              ? `Suggested point: ${escapeHtml(`${formatCoordinate(current.suggestedLatitude)}, ${formatCoordinate(current.suggestedLongitude)}`)}${current.suggestedInsideBoundary === false ? " (outside KMZ)" : ""}`
              : "No suggested point was available for this crash."
          }
        </div>
      </div>
      <div class="wizard-decision-status">${escapeHtml(describeCurrentDecision(current))}</div>
      <div class="wizard-actions">
        <button class="btn secondary small" data-action="wizard-accept-suggested" data-row="${escapeHtml(current.rowKey)}"${canAcceptSuggested ? "" : " disabled"}>Confirm Suggested Placement</button>
        <button class="btn secondary small" data-action="wizard-pick-map" data-row="${escapeHtml(current.rowKey)}">${state.reviewMapPickMode ? "Map Pick Active" : "Pick On Map"}</button>
        <button class="btn secondary small" data-action="wizard-confirm-manual" data-row="${escapeHtml(current.rowKey)}"${draftPlacement && draftInside ? "" : " disabled"}>Confirm Map Placement</button>
        <button class="btn secondary small" data-action="wizard-reject" data-row="${escapeHtml(current.rowKey)}">Reject Crash</button>
        <button class="btn secondary small" data-action="wizard-clear-decision" data-row="${escapeHtml(current.rowKey)}"${decision || draftPlacement ? "" : " disabled"}>Clear Decision</button>
      </div>
      ${
        draftPlacement
          ? `<div class="wizard-draft ${draftInside ? "" : "warn"}">Staged map placement: ${escapeHtml(`${formatCoordinate(draftPlacement.latitude)}, ${formatCoordinate(draftPlacement.longitude)}`)}${draftInside ? "" : " (outside KMZ boundary)"}</div>`
          : ""
      }
      <div class="wizard-nav">
        <button class="btn secondary small" data-action="wizard-prev"${state.currentReviewIndex > 0 ? "" : " disabled"}>Previous</button>
        <button class="btn secondary small" data-action="wizard-next"${state.currentReviewIndex < visibleSteps.length - 1 ? "" : " disabled"}>Next</button>
        ${
          navigationSecondaryLabel
            ? `<button class="btn secondary small" data-action="toggle-secondary">${escapeHtml(navigationSecondaryLabel)}</button>`
            : ""
        }
      </div>
    </section>
  `;

  renderReviewMap();
  updateBrowserReviewButton();
}

async function fetchReviewQueue(runId) {
  if (!runId) {
    state.reviewQueue = [];
    state.reviewSecondaryQueue = [];
    state.reviewMapData = null;
    state.reviewDecisions = {};
    state.reviewDraftPlacements = {};
    state.currentReviewIndex = 0;
    state.showSecondaryReview = false;
    state.reviewMapPickMode = false;
    state.reviewMapFocusKey = null;
    renderReviewQueue();
    return;
  }
  const response = await fetch(`/api/run/${runId}/review-wizard`);
  if (!response.ok) {
    state.reviewQueue = [];
    state.reviewSecondaryQueue = [];
    state.reviewMapData = null;
    state.reviewDecisions = {};
    state.reviewDraftPlacements = {};
    state.showSecondaryReview = false;
    state.currentReviewIndex = 0;
    state.reviewMapPickMode = false;
    state.reviewMapFocusKey = null;
    renderReviewQueue();
    return;
  }
  const data = await response.json().catch(() => ({}));
  state.reviewQueue = data.primarySteps || [];
  state.reviewSecondaryQueue = data.secondarySteps || [];
  state.reviewMapData = data.mapData || null;
  const validKeys = new Set(
    [...state.reviewQueue, ...state.reviewSecondaryQueue].map((step) => step.rowKey)
  );
  state.reviewDecisions = Object.fromEntries(
    Object.entries(state.reviewDecisions).filter(([key]) => validKeys.has(key))
  );
  state.reviewDraftPlacements = Object.fromEntries(
    Object.entries(state.reviewDraftPlacements).filter(([key]) => validKeys.has(key))
  );
  state.currentReviewIndex = 0;
  state.showSecondaryReview = false;
  state.reviewMapPickMode = false;
  state.reviewMapFocusKey = null;
  renderReviewQueue();
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function escapeHtmlWithBreaks(value) {
  return escapeHtml(value).replaceAll("\n", "<br />");
}

function confirmSuggestedPlacement(rowKey) {
  const step = findReviewStep(rowKey);
  if (!step || !step.hasSuggestion || step.suggestedInsideBoundary === false) {
    return;
  }
  focusReviewStep(rowKey);
  delete state.reviewDraftPlacements[rowKey];
  state.reviewMapPickMode = false;
  state.reviewMapFocusKey = null;
  state.reviewDecisions[rowKey] = {
    rowKey,
    latitude: step.suggestedLatitude,
    longitude: step.suggestedLongitude,
    action: "apply",
    placementMode: "suggested",
    note: "Confirmed suggested placement in browser review wizard.",
  };
  moveToNextReviewStep(true);
  renderReviewQueue();
}

function beginMapPlacement(rowKey) {
  const current = getCurrentReviewStep();
  const togglingCurrentStep = current && current.rowKey === rowKey && state.reviewMapPickMode;
  focusReviewStep(rowKey);
  state.reviewMapPickMode = !togglingCurrentStep;
  state.reviewMapFocusKey = null;
  renderReviewQueue();
  if (state.reviewMapPickMode) {
    showToast("Click inside the KMZ boundary to stage a custom placement.");
  }
}

function confirmManualPlacement(rowKey) {
  const step = findReviewStep(rowKey);
  const draftPlacement = step ? getDraftPlacement(step) : null;
  if (!step || !draftPlacement) {
    showToast("Stage a map placement before confirming it.");
    return;
  }
  if (!pointInProjectBoundary(draftPlacement.latitude, draftPlacement.longitude)) {
    showToast("Map placement must stay inside the KMZ boundary.");
    return;
  }
  focusReviewStep(rowKey);
  state.reviewMapPickMode = false;
  state.reviewMapFocusKey = null;
  state.reviewDecisions[rowKey] = {
    rowKey,
    latitude: draftPlacement.latitude,
    longitude: draftPlacement.longitude,
    action: "apply",
    placementMode: "manual",
    note: "Confirmed manual map placement in browser review wizard.",
  };
  delete state.reviewDraftPlacements[rowKey];
  moveToNextReviewStep(true);
  renderReviewQueue();
}

function rejectReviewCrash(rowKey) {
  if (!findReviewStep(rowKey)) {
    return;
  }
  focusReviewStep(rowKey);
  delete state.reviewDraftPlacements[rowKey];
  state.reviewMapPickMode = false;
  state.reviewMapFocusKey = null;
  state.reviewDecisions[rowKey] = {
    rowKey,
    action: "reject",
    note: "Rejected in browser review wizard.",
  };
  moveToNextReviewStep(true);
  renderReviewQueue();
}

function clearReviewDecision(rowKey) {
  delete state.reviewDecisions[rowKey];
  delete state.reviewDraftPlacements[rowKey];
  state.reviewMapPickMode = false;
  state.reviewMapFocusKey = null;
  renderReviewQueue();
}

function clearCurrentMapPlacement() {
  const current = getCurrentReviewStep();
  if (!current) {
    return;
  }
  delete state.reviewDraftPlacements[current.rowKey];
  state.reviewMapPickMode = false;
  state.reviewMapFocusKey = null;
  renderReviewQueue();
}

async function startRun() {
  if (!state.dataFile || !state.kmzFile) return;
  clearLogs();
  state.reviewQueue = [];
  state.reviewSecondaryQueue = [];
  state.reviewDecisions = {};
  state.reviewDraftPlacements = {};
  state.currentReviewIndex = 0;
  state.showSecondaryReview = false;
  state.reviewMapData = null;
  state.reviewMapPickMode = false;
  state.reviewMapFocusKey = null;
  renderReviewQueue();
  setStatus("running", "Refinement running", "Crash data pipeline is processing.");
  setProgressRunning(true);
  setReportProgressRunning(false);
  el.runRefine.disabled = true;
  el.generateReport.disabled = true;
  el.applyReview.disabled = true;
  el.snapshotTag.textContent = "Running";
  el.snapshotStatus.textContent = "Processing crash data.";
  el.outputLinks.textContent = "Run in progress...";

  const response = await fetch("/api/run", {
    method: "POST",
    body: buildRunFormData(),
  });
  const data = await response.json();
  if (!response.ok) {
    showToast(data.error || "Unable to start refinement.");
    setStatus("error", "Run failed to start", "Check inputs and try again.");
    setProgressRunning(false);
    updateRunButton();
    return;
  }
  state.runId = data.runId;
  state.logSeq = 0;
  pollLogs();
  state.pollTimer = window.setInterval(pollLogs, 1200);
}

async function startReport() {
  if (!state.pdfDataFile && !state.runId && !state.dataFile) {
    showToast("Select a crash data or PDF report file first.");
    return;
  }
  clearLogs();
  setStatus("running", "Report running", "Generating PDF crash report.");
  setProgressRunning(true);
  setReportProgressRunning(true);
  el.runRefine.disabled = true;
  el.generateReport.disabled = true;
  el.applyReview.disabled = true;
  el.snapshotTag.textContent = "Running";
  el.snapshotStatus.textContent = "Generating PDF report.";
  el.outputLinks.textContent = "Report in progress...";
  setMapPreview(null);

  const response = await fetch("/api/report", {
    method: "POST",
    body: buildReportFormData(),
  });
  const data = await response.json();
  if (!response.ok) {
    showToast(data.error || "Unable to start report.");
    setStatus("error", "Report failed to start", "Check inputs and try again.");
    setProgressRunning(false);
    setReportProgressRunning(false);
    updateRunButton();
    return;
  }
  state.runId = data.runId;
  state.logSeq = 0;
  pollLogs();
  state.pollTimer = window.setInterval(pollLogs, 1200);
}

async function startApplyReview() {
  if (!state.runId || !state.reviewFile) {
    showToast("Run refinement first, then upload a reviewed coordinate workbook.");
    return;
  }
  clearLogs();
  setStatus("running", "Applying review decisions", "Re-running refinement with approved coordinates.");
  setProgressRunning(true);
  setReportProgressRunning(false);
  el.runRefine.disabled = true;
  el.generateReport.disabled = true;
  el.applyReview.disabled = true;
  el.snapshotTag.textContent = "Running";
  el.snapshotStatus.textContent = "Applying approved coordinate decisions.";
  el.outputLinks.textContent = "Run in progress...";

  const response = await fetch("/api/apply-review", {
    method: "POST",
    body: buildReviewFormData(),
  });
  const data = await response.json();
  if (!response.ok) {
    showToast(data.error || "Unable to apply coordinate decisions.");
    setStatus("error", "Review apply failed", "Check the reviewed workbook and try again.");
    setProgressRunning(false);
    updateRunButton();
    return;
  }
  state.reviewFile = null;
  state.reviewQueue = [];
  state.reviewSecondaryQueue = [];
  state.reviewDecisions = {};
  state.reviewDraftPlacements = {};
  state.currentReviewIndex = 0;
  state.showSecondaryReview = false;
  state.reviewMapData = null;
  state.reviewMapPickMode = false;
  state.reviewMapFocusKey = null;
  renderReviewQueue();
  el.reviewInput.value = "";
  el.reviewLabel.textContent = "Drop reviewed Coordinate Recovery workbook";
  el.reviewHint.textContent = "Download, fill approved coordinates, then upload it here.";
  state.runId = data.runId;
  state.logSeq = 0;
  pollLogs();
  state.pollTimer = window.setInterval(pollLogs, 1200);
}

async function startApplyBrowserReview() {
  if (!state.runId || Object.keys(state.reviewDecisions).length === 0) {
    showToast("Select at least one coordinate decision first.");
    return;
  }
  clearLogs();
  setStatus("running", "Applying browser review", "Re-running refinement with reviewed crash placements.");
  setProgressRunning(true);
  setReportProgressRunning(false);
  el.runRefine.disabled = true;
  el.generateReport.disabled = true;
  el.applyReview.disabled = true;
  el.applyBrowserReview.disabled = true;
  el.snapshotTag.textContent = "Running";
  el.snapshotStatus.textContent = "Applying selected crash review decisions.";
  el.outputLinks.textContent = "Run in progress...";

  const response = await fetch("/api/apply-review", {
    method: "POST",
    body: buildBrowserReviewFormData(),
  });
  const data = await response.json();
  if (!response.ok) {
    showToast(data.error || "Unable to apply browser review decisions.");
    setStatus("error", "Browser review failed", "Check the selected decisions and try again.");
    setProgressRunning(false);
    updateRunButton();
    return;
  }
  state.reviewQueue = [];
  state.reviewSecondaryQueue = [];
  state.reviewDecisions = {};
  state.reviewDraftPlacements = {};
  state.currentReviewIndex = 0;
  state.showSecondaryReview = false;
  state.reviewMapData = null;
  state.reviewMapPickMode = false;
  state.reviewMapFocusKey = null;
  renderReviewQueue();
  state.runId = data.runId;
  state.logSeq = 0;
  pollLogs();
  state.pollTimer = window.setInterval(pollLogs, 1200);
}

async function pollLogs() {
  if (!state.runId) return;
  const response = await fetch(`/api/run/${state.runId}/log?since=${state.logSeq}`);
  if (!response.ok) return;
  const data = await response.json();
  state.logSeq = data.lastSeq || state.logSeq;
  appendLog(data.entries || []);
  if (data.status === "running" && data.message) {
    el.statusDetail.textContent = data.message;
    el.snapshotStatus.textContent = data.message;
  }
  if (data.status && data.status !== "running") {
    window.clearInterval(state.pollTimer);
    state.pollTimer = null;
    await finalizeRun(data.status);
  }
}

async function finalizeRun(status) {
  const response = await fetch(`/api/run/${state.runId}`);
  if (!response.ok) {
    setStatus("error", "Run failed", "Unable to retrieve run status.");
    setProgressRunning(false);
    state.reviewQueue = [];
    renderReviewQueue();
    updateRunButton();
    return;
  }
  const data = await response.json();
  const runKind = (data.inputs && data.inputs.runKind) || "refine";
  const usedReviewWorkbook = !!(
    data.inputs && (data.inputs.coordinateReviewFile || data.inputs.browserReviewDecisionCount)
  );
  if (status === "success") {
    const successTitle = runKind === "report"
      ? "Report complete"
      : (usedReviewWorkbook ? "Review decisions applied" : "Refinement complete");
    const successSnapshot = runKind === "report"
      ? "PDF report completed successfully."
      : (usedReviewWorkbook
        ? "Refinement reran with approved coordinates."
        : "Refinement completed successfully.");
    setStatus(
      "success",
      successTitle,
      data.message || "Outputs ready."
    );
    el.snapshotTag.textContent = "Complete";
    el.snapshotStatus.textContent = successSnapshot;
  } else {
    const errorTitle = runKind === "report"
      ? "Report failed"
      : (usedReviewWorkbook ? "Review apply failed" : "Refinement failed");
    const errorSnapshot = runKind === "report"
      ? "PDF report encountered errors."
      : (usedReviewWorkbook
        ? "Approved coordinate rerun encountered errors."
        : "Refinement encountered errors.");
    const errorToast = runKind === "report"
      ? "PDF report failed."
      : (usedReviewWorkbook ? "Applying review decisions failed." : "Refinement failed.");
    setStatus(
      "error",
      errorTitle,
      data.message || "Review the run log."
    );
    el.snapshotTag.textContent = "Failed";
    el.snapshotStatus.textContent = errorSnapshot;
    showToast(data.error || errorToast);
  }

  renderOutputs(data.outputs || []);
  renderMetrics(data.summary || {});
  if (data.summary && data.summary.mapReport) {
    setMapPreview(data.summary.mapReport);
  }
  if (status === "success") {
    await fetchReviewQueue(state.runId);
  } else {
    renderReviewQueue();
  }

  const finishedAt = data.finishedAt;
  if (finishedAt) {
    el.snapshotLastRun.textContent = `Completed ${new Date(finishedAt).toLocaleString()}`;
  }
  setProgressRunning(false);
  setReportProgressRunning(false);
  updateRunButton();
}

function syncLogWindow() {
  if (!state.logWindow || state.logWindow.closed) return;
  const doc = state.logWindow.document;
  const container = doc.getElementById("log-stream");
  if (!container) return;
  container.textContent = state.logLines.join("\n");
}

function openLogWindow() {
  if (state.logWindow && !state.logWindow.closed) {
    state.logWindow.focus();
    return;
  }
  state.logWindow = window.open("", "runlog", "width=900,height=600");
  if (!state.logWindow) return;
  state.logWindow.document.write(`
    <html>
      <head>
        <title>Run Log</title>
        <style>
          body { margin: 0; background: #010201; color: #00ff41; font-family: "Courier New", monospace; }
          pre { margin: 0; padding: 18px; white-space: pre-wrap; }
        </style>
      </head>
      <body>
        <pre id="log-stream"></pre>
      </body>
    </html>
  `);
  state.logWindow.document.close();
  syncLogWindow();
}

function setupDropZone(zone, input, handler) {
  zone.addEventListener("dragover", (event) => {
    event.preventDefault();
    zone.classList.add("dragover");
  });
  zone.addEventListener("dragleave", () => zone.classList.remove("dragover"));
  zone.addEventListener("drop", (event) => {
    event.preventDefault();
    zone.classList.remove("dragover");
    const file = event.dataTransfer.files[0];
    if (file) handler(file);
  });
  input.addEventListener("change", (event) => {
    const file = event.target.files[0];
    if (file) handler(file);
  });
}

function validateDataFile(file) {
  const name = file.name.toLowerCase();
  return name.endsWith(".csv") || name.endsWith(".xlsx") || name.endsWith(".xlsm");
}

function validateKmzFile(file) {
  return file.name.toLowerCase().endsWith(".kmz");
}

function bindInputs() {
  el.latColumn.addEventListener("input", () => {
    updateSummary();
    updateRunButton();
    schedulePreviewMap();
  });
  el.lonColumn.addEventListener("input", () => {
    updateSummary();
    updateRunButton();
    schedulePreviewMap();
  });
  el.runRefine.addEventListener("click", startRun);
  el.generateReport.addEventListener("click", startReport);
  el.applyReview.addEventListener("click", startApplyReview);
  el.applyBrowserReview.addEventListener("click", startApplyBrowserReview);
  el.reviewList.addEventListener("click", (event) => {
    const target = event.target.closest("[data-action]");
    if (!target) return;
    if (target.dataset.action === "toggle-secondary") {
      state.showSecondaryReview = !state.showSecondaryReview;
      state.reviewMapPickMode = false;
      state.reviewMapFocusKey = null;
      renderReviewQueue();
      return;
    }
    if (target.dataset.action === "wizard-prev") {
      state.reviewMapPickMode = false;
      moveToPreviousReviewStep();
      state.reviewMapFocusKey = null;
      renderReviewQueue();
      return;
    }
    if (target.dataset.action === "wizard-next") {
      state.reviewMapPickMode = false;
      moveToNextReviewStep();
      state.reviewMapFocusKey = null;
      renderReviewQueue();
      return;
    }
    const rowKey = target.dataset.row;
    if (!rowKey) return;
    if (target.dataset.action === "wizard-accept-suggested") {
      confirmSuggestedPlacement(rowKey);
      return;
    }
    if (target.dataset.action === "wizard-pick-map") {
      beginMapPlacement(rowKey);
      return;
    }
    if (target.dataset.action === "wizard-confirm-manual") {
      confirmManualPlacement(rowKey);
      return;
    }
    if (target.dataset.action === "wizard-reject") {
      rejectReviewCrash(rowKey);
      return;
    }
    if (target.dataset.action === "wizard-clear-decision") {
      clearReviewDecision(rowKey);
    }
  });
  el.clearMapSelection.addEventListener("click", clearCurrentMapPlacement);
  el.clearSession.addEventListener("click", () => {
    if (state.pollTimer) {
      window.clearInterval(state.pollTimer);
      state.pollTimer = null;
    }
    if (state.previewTimer) {
      window.clearTimeout(state.previewTimer);
      state.previewTimer = null;
    }
    state.previewRequestId = 0;
    state.runId = null;
    state.logSeq = 0;
    clearLogs();
    state.dataFile = null;
    state.kmzFile = null;
    state.pdfDataFile = null;
    state.reviewFile = null;
    state.reviewQueue = [];
    state.reviewSecondaryQueue = [];
    state.reviewDecisions = {};
    state.reviewDraftPlacements = {};
    state.currentReviewIndex = 0;
    state.showSecondaryReview = false;
    state.reviewMapData = null;
    state.reviewMapPickMode = false;
    state.reviewMapFocusKey = null;
    el.dataInput.value = "";
    el.kmzInput.value = "";
    el.pdfInput.value = "";
    el.reviewInput.value = "";
    el.latColumn.value = "";
    el.lonColumn.value = "";
    el.labelOrder.selectedIndex = 0;
    el.dataLabel.textContent = "Drop crash data (CSV or Excel)";
    el.dataHint.textContent = "Drag a file here or click to browse.";
    el.kmzLabel.textContent = "Drop KMZ polygon boundary";
    el.kmzHint.textContent = "Must contain exactly one polygon.";
    el.pdfLabel.textContent = "Drop alternate PDF data file";
    el.pdfHint.textContent = "Leave blank to use refined output when available.";
    el.reviewLabel.textContent = "Drop reviewed Coordinate Recovery workbook";
    el.reviewHint.textContent = "Download, fill approved coordinates, then upload it here.";
    updateColumnOptions([]);
    setStatus("idle", "Ready to run", "Add crash data and a KMZ polygon to begin refinement.");
    setProgressRunning(false);
    el.snapshotTag.textContent = "Idle";
    el.snapshotStatus.textContent = "Waiting for inputs.";
    el.snapshotLastRun.textContent = "No runs yet.";
    el.outputLinks.textContent = "No outputs yet.";
    el.metrics.innerHTML = "";
    el.mapPlaceholder.textContent = "Map preview appears after crash data and boundary files are loaded.";
    setMapPreview(null);
    renderReviewQueue();
    setReportProgressRunning(false);
    updateSummary();
    updateRunButton();
  });
  el.popLog.addEventListener("click", openLogWindow);
  el.openMap.addEventListener("click", () => {
    const url = el.openMap.dataset.url;
    if (url) window.open(url, "_blank");
  });
}

function wireModals() {
  el.openGuide.addEventListener("click", () => el.guideModal.showModal());
  el.openNotes.addEventListener("click", () => el.notesModal.showModal());
  document.querySelectorAll("[data-close]").forEach((button) => {
    button.addEventListener("click", () => {
      const dialog = button.closest("dialog");
      if (dialog) dialog.close();
    });
  });
}

function init() {
  wireModals();
  bindInputs();
  setupDropZone(el.dataDrop, el.dataInput, (file) => {
    if (!validateDataFile(file)) {
      showToast("Crash data must be a CSV or Excel file.");
      return;
    }
    state.dataFile = file;
    el.latColumn.value = "";
    el.lonColumn.value = "";
    el.dataLabel.textContent = file.name;
    el.dataHint.textContent = "Crash data ready. Confirm columns and run refinement.";
    fetchHeaders(file);
    updateSummary();
    updateRunButton();
    schedulePreviewMap();
  });
  setupDropZone(el.kmzDrop, el.kmzInput, (file) => {
    if (!validateKmzFile(file)) {
      showToast("KMZ boundary must be a .kmz file.");
      return;
    }
    state.kmzFile = file;
    el.kmzLabel.textContent = file.name;
    el.kmzHint.textContent = "Boundary loaded. Ready to run.";
    updateSummary();
    updateRunButton();
    schedulePreviewMap();
  });
  setupDropZone(el.pdfDrop, el.pdfInput, (file) => {
    if (!validateDataFile(file)) {
      showToast("PDF data must be a CSV or Excel file.");
      return;
    }
    state.pdfDataFile = file;
    el.pdfLabel.textContent = file.name;
    el.pdfHint.textContent = "PDF will use this dataset.";
    updateSummary();
    updateRunButton();
  });
  setupDropZone(el.reviewDrop, el.reviewInput, (file) => {
    if (!validateDataFile(file)) {
      showToast("Coordinate review data must be a CSV or Excel file.");
      return;
    }
    state.reviewFile = file;
    el.reviewLabel.textContent = file.name;
    el.reviewHint.textContent = state.runId
      ? "Ready to re-run refinement with approved coordinate decisions."
      : "Run refinement first, then apply this reviewed workbook.";
    updateSummary();
    updateRunButton();
  });
  window.addEventListener("dragover", (event) => event.preventDefault());
  window.addEventListener("drop", (event) => event.preventDefault());
  updateSummary();
  renderReviewQueue();
  updateRunButton();
  setReportProgressRunning(false);
  updateReviewButton();
}

init();
