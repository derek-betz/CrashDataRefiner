const state = {
  dataFile: null,
  kmzFile: null,
  pdfDataFile: null,
  reviewFile: null,
  runInputs: null,
  lastRunSummary: null,
  lastOutputs: [],
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
  reviewWorkbenchTab: "map",
  reviewExcludeConfirmRow: null,
  uiStage: "inputs",
  advancedToolsOpen: false,
  detailsPanelOpen: false,
  isBootstrappingUi: true,
  isRestoringSession: false,
  runId: null,
  logSeq: 0,
  logLines: [],
  pollTimer: null,
  logWindow: null,
  mapReportName: null,
  previewTimer: null,
  previewRequestId: 0,
  headerRequestId: 0,
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
  labelOrderHint: document.getElementById("label-order-hint"),
  columnOptions: document.getElementById("column-options"),
  columnHint: document.getElementById("column-hint"),
  columnLoadingIndicator: document.getElementById("column-loading-indicator"),
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
  stageKicker: document.getElementById("stage-kicker"),
  stageTitle: document.getElementById("stage-title"),
  stageDescription: document.getElementById("stage-description"),
  stageFiles: document.getElementById("stage-files"),
  stageNext: document.getElementById("stage-next"),
  stageViewInputs: document.getElementById("stage-view-inputs"),
  stageViewReview: document.getElementById("stage-view-review"),
  stageViewResults: document.getElementById("stage-view-results"),
  stageStepInputs: document.getElementById("stage-step-inputs"),
  stageStepReview: document.getElementById("stage-step-review"),
  stageStepResults: document.getElementById("stage-step-results"),
  advancedToolsPanel: document.getElementById("advanced-tools-panel"),
  inputShell: document.querySelector(".input-shell"),
  checkDataStatus: document.getElementById("check-data-status"),
  checkKmzStatus: document.getElementById("check-kmz-status"),
  checkColumnsStatus: document.getElementById("check-columns-status"),
  mapFrame: document.getElementById("map-frame"),
  mapPlaceholder: document.getElementById("map-placeholder"),
  inputMapFrame: document.getElementById("input-map-frame"),
  inputMapPlaceholder: document.getElementById("input-map-placeholder"),
  mapSubtitle: document.getElementById("map-subtitle"),
  mapMode: document.getElementById("map-mode"),
  wizardMap: document.getElementById("wizard-map"),
  wizardMapToolbar: document.getElementById("wizard-map-toolbar"),
  wizardMapSelection: document.getElementById("wizard-map-selection"),
  clearMapSelection: document.getElementById("clear-map-selection"),
  inputOpenMap: document.getElementById("input-open-map"),
  openMap: document.getElementById("open-map"),
  reviewList: document.getElementById("review-list"),
  reviewSummary: document.getElementById("review-summary"),
  reviewQueueSubtitle: document.getElementById("review-queue-subtitle"),
  reviewWorkbench: document.getElementById("review-workbench"),
  reviewWorkbenchTabs: document.getElementById("review-workbench-tabs"),
  reviewTabDetails: document.getElementById("review-tab-details"),
  reviewTabMap: document.getElementById("review-tab-map"),
  reviewStageCount: document.getElementById("review-stage-count"),
  reviewStageTotals: document.getElementById("review-stage-totals"),
  reviewStageNote: document.getElementById("review-stage-note"),
  reviewStageProgressFill: document.getElementById("review-stage-progressfill"),
  applyBrowserReview: document.getElementById("apply-browser-review"),
  reviewSkipToResults: document.getElementById("review-skip-to-results"),
  resultsSummaryLine: document.getElementById("results-summary-line"),
  resultsGenerateReport: document.getElementById("results-generate-report"),
  resultsOpenMap: document.getElementById("results-open-map"),
  resultsResumeReview: document.getElementById("results-resume-review"),
  resultsLabelOrder: document.getElementById("results-label-order"),
  resultsLabelOrderStatus: document.getElementById("results-label-order-status"),
  resultsRelabel: document.getElementById("results-relabel"),
  technicalDetails: document.getElementById("technical-details"),
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
  if (el.statusTitle) {
    el.statusTitle.textContent = title;
  }
  if (el.statusDetail) {
    el.statusDetail.textContent = detail;
  }
  saveUiSession();
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
  if (el.stageStepInputs) {
    el.stageStepInputs.disabled = false;
  }
  updateReportButton();
  updateReviewButton();
  updateRelabelButton();
  updateReadinessChecklist();
  updateStageAvailability();
  updateLabelOrderControls();
  renderStageChrome();
}

function updateReportButton() {
  const hasSource = !!state.pdfDataFile || !!state.runId || !!state.dataFile;
  el.generateReport.disabled = !hasSource;
  if (el.resultsGenerateReport) {
    el.resultsGenerateReport.disabled = !hasSource;
  }
}

function updateReviewButton() {
  const hasSourceRun = !!state.runId;
  const hasReviewFile = !!state.reviewFile;
  el.applyReview.disabled = !(hasSourceRun && hasReviewFile);
  updateBrowserReviewButton();
}

function updateRelabelButton() {
  if (el.resultsRelabel) {
    el.resultsRelabel.disabled = !state.runId;
  }
}

function updateBrowserReviewButton() {
  const selectedCount = Object.keys(state.reviewDecisions).length;
  const recommendResults = reviewResultsRecommended();
  el.applyBrowserReview.disabled = !(state.runId && selectedCount > 0);
  el.applyBrowserReview.classList.toggle(
    "is-ready",
    !!state.runId && reviewPendingCount() > 0 && selectedCount === reviewPendingCount()
  );
  if (el.reviewSkipToResults) {
    el.reviewSkipToResults.hidden = !(state.runId && (recommendResults || (selectedCount === 0 && reviewPendingCount() > 0)));
    el.reviewSkipToResults.textContent = recommendResults ? "Continue to results" : "Skip to results";
  }
  updateReviewStageHeader();
  saveUiSession();
}

function isReviewWorkbenchTabbed() {
  return window.matchMedia("(max-width: 1180px)").matches;
}

function setReviewWorkbenchTab(tab) {
  state.reviewWorkbenchTab = tab === "map" ? "map" : "details";
  if (el.reviewWorkbench) {
    el.reviewWorkbench.dataset.activeTab = state.reviewWorkbenchTab;
  }
  if (el.reviewTabDetails) {
    el.reviewTabDetails.classList.toggle("is-active", state.reviewWorkbenchTab === "details");
  }
  if (el.reviewTabMap) {
    el.reviewTabMap.classList.toggle("is-active", state.reviewWorkbenchTab === "map");
  }
}

function clearPendingExclusion(rowKey = null) {
  if (!rowKey || state.reviewExcludeConfirmRow === rowKey) {
    state.reviewExcludeConfirmRow = null;
  }
}

const SESSION_KEY = "crash-data-refiner-ui-state";

function saveUiSession() {
  if (state.isBootstrappingUi || state.isRestoringSession) {
    return;
  }
  const payload = {
    runId: state.runId,
    uiStage: state.uiStage,
    currentReviewIndex: state.currentReviewIndex,
    reviewWorkbenchTab: state.reviewWorkbenchTab,
    showSecondaryReview: state.showSecondaryReview,
    reviewDecisions: state.reviewDecisions,
    reviewDraftPlacements: state.reviewDraftPlacements,
    reviewExcludeConfirmRow: state.reviewExcludeConfirmRow,
    runInputs: state.runInputs,
    lastRunSummary: state.lastRunSummary,
    lastOutputs: state.lastOutputs,
    detailsPanelOpen: state.detailsPanelOpen,
    advancedToolsOpen: state.advancedToolsOpen,
  };
  window.sessionStorage.setItem(SESSION_KEY, JSON.stringify(payload));
}

function clearUiSession() {
  window.sessionStorage.removeItem(SESSION_KEY);
}

function readUiSession() {
  const raw = window.sessionStorage.getItem(SESSION_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw);
  } catch (_error) {
    clearUiSession();
    return null;
  }
}

function setUiStage(stage, { persist = true } = {}) {
  const nextStage = canEnterStage(stage) ? stage : (state.runId ? "results" : "inputs");
  state.uiStage = nextStage;
  const stages = ["inputs", "review", "results"];
  stages.forEach((name) => {
    const view = name === "inputs"
      ? el.stageViewInputs
      : (name === "review" ? el.stageViewReview : el.stageViewResults);
    const step = name === "inputs"
      ? el.stageStepInputs
      : (name === "review" ? el.stageStepReview : el.stageStepResults);
    if (view) {
      view.classList.toggle("is-active", name === state.uiStage);
    }
    if (step) {
      step.classList.toggle("is-active", name === state.uiStage);
    }
  });
  renderStageChrome();
  if (persist) {
    saveUiSession();
  }
}

function setAdvancedToolsOpen(isOpen) {
  state.advancedToolsOpen = !!isOpen;
  if (el.advancedToolsPanel) {
    el.advancedToolsPanel.open = state.advancedToolsOpen;
  }
  saveUiSession();
}

function setTechnicalDetailsOpen(isOpen) {
  state.detailsPanelOpen = !!isOpen;
  if (el.technicalDetails) {
    el.technicalDetails.open = state.detailsPanelOpen;
  }
  saveUiSession();
}

function resetTransientInputUi() {
  el.dataInput.value = "";
  el.kmzInput.value = "";
  el.pdfInput.value = "";
  el.reviewInput.value = "";
  el.latColumn.value = "";
  el.lonColumn.value = "";
  el.dataLabel.textContent = "Crash spreadsheet (.csv, .xlsx)";
  el.dataHint.textContent = "Drop file or click to browse";
  el.kmzLabel.textContent = "Boundary KMZ (.kmz)";
  el.kmzHint.textContent = "One polygon only";
  el.pdfLabel.textContent = "Alternate PDF source (.csv, .xlsx)";
  el.pdfHint.textContent = "Optional";
  el.reviewLabel.textContent = "Reviewed coordinate workbook";
  el.reviewHint.textContent = "Upload a reviewed workbook";
  if (el.columnHint) {
    el.columnHint.hidden = false;
    el.columnHint.textContent = "Columns will populate automatically after upload.";
  }
  updateColumnOptions([]);
  setLabelOrderSelection("auto", { scope: "input" });
}

function previewSurfaces() {
  return [
    {
      frame: el.inputMapFrame,
      placeholder: el.inputMapPlaceholder,
      button: el.inputOpenMap,
      emptyMessage: "Load a spreadsheet and KMZ to preview the project map.",
    },
    {
      frame: el.mapFrame,
      placeholder: el.mapPlaceholder,
      button: el.openMap,
      emptyMessage: "The map appears here once files are loaded.",
    },
  ].filter((surface) => surface.frame && surface.placeholder);
}

function resetPreviewSurface(surface, message = surface.emptyMessage) {
  surface.frame.dataset.loaded = "false";
  surface.frame.removeAttribute("src");
  surface.placeholder.textContent = message;
  surface.placeholder.style.display = "flex";
  if (surface.button) {
    surface.button.disabled = true;
    delete surface.button.dataset.url;
  }
}

function loadPreviewSurface(surface, url) {
  surface.frame.dataset.loaded = "false";
  surface.placeholder.textContent = "Loading map...";
  surface.placeholder.style.display = "flex";
  surface.frame.src = url;
  if (surface.button) {
    surface.button.disabled = false;
    surface.button.dataset.url = url;
  }
}

function bindPreviewSurface(frame, placeholder) {
  if (!frame || !placeholder) return;
  frame.addEventListener("load", () => {
    if (frame.getAttribute("src")) {
      frame.dataset.loaded = "true";
      placeholder.style.display = "none";
    }
  });
  frame.addEventListener("error", () => {
    frame.dataset.loaded = "false";
    placeholder.textContent = "Map preview unavailable.";
    placeholder.style.display = "flex";
  });
}

function getDisplayRunInputs() {
  const useSavedInputs = state.uiStage !== "inputs" && !!state.runId;
  return {
    dataFile: state.dataFile ? state.dataFile.name : (useSavedInputs ? (state.runInputs && state.runInputs.dataFile) || "" : ""),
    kmzFile: state.kmzFile ? state.kmzFile.name : (useSavedInputs ? (state.runInputs && state.runInputs.kmzFile) || "" : ""),
    latColumn: el.latColumn.value.trim() || (useSavedInputs ? (state.runInputs && state.runInputs.latColumn) || "" : ""),
    lonColumn: el.lonColumn.value.trim() || (useSavedInputs ? (state.runInputs && state.runInputs.lonColumn) || "" : ""),
  };
}

function renderStageFiles() {
  if (!el.stageFiles) return;
  const info = getDisplayRunInputs();
  const items = [];
  if (info.dataFile) {
    items.push(`<div class="workflow-file">Crash spreadsheet: ${escapeHtml(info.dataFile)}</div>`);
  }
  if (info.kmzFile) {
    items.push(`<div class="workflow-file">Boundary KMZ: ${escapeHtml(info.kmzFile)}</div>`);
  }
  if (info.latColumn && info.lonColumn) {
    items.push(`<div class="workflow-file">Columns: ${escapeHtml(info.latColumn)} / ${escapeHtml(info.lonColumn)}</div>`);
  }
  if (!items.length) {
    items.push('<div class="workflow-file empty">No project files loaded yet.</div>');
  }
  el.stageFiles.innerHTML = items.join("");
}

function formatLabelOrder(value) {
  if (value === "south_to_north") {
    return "bottom to top (south to north)";
  }
  if (value === "west_to_east") {
    return "left to right (west to east)";
  }
  return "automatic";
}

function getRequestedLabelOrder() {
  return (
    (state.lastRunSummary && state.lastRunSummary.labelOrdering && state.lastRunSummary.labelOrdering.requested)
    || (state.runInputs && state.runInputs.labelOrder)
    || "auto"
  );
}

function getResolvedLabelOrder() {
  return (
    (state.lastRunSummary && state.lastRunSummary.labelOrdering && state.lastRunSummary.labelOrdering.resolved)
    || (state.runInputs && state.runInputs.resolvedLabelOrder)
    || (getRequestedLabelOrder() === "auto" ? "west_to_east" : getRequestedLabelOrder())
  );
}

function setLabelOrderSelection(value, { scope = "both", syncState = false } = {}) {
  const normalized = value === "south_to_north" || value === "west_to_east" ? value : "auto";
  if ((scope === "both" || scope === "input") && el.labelOrder && el.labelOrder.value !== normalized) {
    el.labelOrder.value = normalized;
  }
  if ((scope === "both" || scope === "results") && el.resultsLabelOrder && el.resultsLabelOrder.value !== normalized) {
    el.resultsLabelOrder.value = normalized;
  }
  if (syncState && state.runInputs) {
    state.runInputs = {
      ...state.runInputs,
      labelOrder: normalized,
    };
  }
  updateLabelOrderControls();
}

function updateLabelOrderControls() {
  const requested = getRequestedLabelOrder();
  const resolved = getResolvedLabelOrder();
  const inputSelection = (el.labelOrder && el.labelOrder.value) || "auto";
  if (el.resultsLabelOrderStatus) {
    el.resultsLabelOrderStatus.textContent = state.runId
      ? (
        requested === "auto"
          ? `Current output order: ${formatLabelOrder(resolved)}.`
          : `Current output order: ${formatLabelOrder(resolved)}.`
      )
      : "Choose how crash labels should be ordered.";
  }
  if (el.labelOrderHint) {
    el.labelOrderHint.textContent = inputSelection === "auto"
      ? "Automatic selection is active."
      : `Override: ${formatLabelOrder(inputSelection)}.`;
  }
}

function reviewPendingCount() {
  return (state.reviewQueue || []).length + (state.reviewSecondaryQueue || []).length;
}

function reviewResultsRecommended() {
  return !!state.runId && !(state.reviewQueue || []).length && !state.showSecondaryReview;
}

function canEnterStage(stage) {
  if (stage === "review") {
    return reviewPendingCount() > 0;
  }
  if (stage === "results") {
    return !!state.runId;
  }
  return true;
}

function renderStageChrome() {
  renderStageFiles();
  if (state.uiStage === "inputs") {
    if (el.stageKicker) el.stageKicker.textContent = "Step 1 of 3";
    if (el.stageTitle) el.stageTitle.textContent = "Load project files";
    if (el.stageDescription) el.stageDescription.textContent = "";
    if (el.stageNext) el.stageNext.textContent = "";
    return;
  }

  if (state.uiStage === "review") {
    if (el.stageKicker) el.stageKicker.textContent = "Step 2 of 3";
    if (el.stageTitle) el.stageTitle.textContent = "Review crashes";
    if (el.stageDescription) el.stageDescription.textContent = "";
    if (el.stageNext) el.stageNext.textContent = "";
    return;
  }

  if (el.stageKicker) el.stageKicker.textContent = "Step 3 of 3";
  if (el.stageTitle) el.stageTitle.textContent = "Download outputs";
  if (el.stageDescription) el.stageDescription.textContent = "";
  if (el.stageNext) el.stageNext.textContent = "";
}

function updateReadinessChecklist() {
  const hasData = !!state.dataFile;
  const hasKmz = !!state.kmzFile;
  const hasColumns = !!(el.latColumn.value.trim() && el.lonColumn.value.trim());
  const items = [
    {
      element: el.checkDataStatus,
      title: "Crash spreadsheet loaded",
      detail: hasData ? state.dataFile.name : "No crash spreadsheet selected yet.",
      ready: hasData,
    },
    {
      element: el.checkKmzStatus,
      title: "Project boundary loaded",
      detail: hasKmz ? state.kmzFile.name : "No project boundary KMZ selected yet.",
      ready: hasKmz,
    },
    {
      element: el.checkColumnsStatus,
      title: "Coordinate columns confirmed",
      detail: hasColumns
        ? `${el.latColumn.value.trim()} / ${el.lonColumn.value.trim()}`
        : "Select the latitude and longitude columns.",
      ready: hasColumns,
    },
  ];

  items.forEach(({ element, title, detail, ready }) => {
    if (!element) return;
    element.classList.toggle("ready", ready);
    const titleEl = element.querySelector(".readiness-title");
    const detailEl = element.querySelector(".readiness-detail");
    if (titleEl) titleEl.textContent = title;
    if (detailEl) detailEl.textContent = detail;
  });
}

function updateStageAvailability() {
  if (el.stageStepReview) {
    el.stageStepReview.disabled = !reviewPendingCount();
  }
  if (el.stageStepResults) {
    el.stageStepResults.disabled = !state.runId;
  }
  if (el.resultsResumeReview) {
    el.resultsResumeReview.hidden = !reviewPendingCount();
  }
}

function metricValue(label) {
  const metrics = state.lastRunSummary && Array.isArray(state.lastRunSummary.metrics)
    ? state.lastRunSummary.metrics
    : [];
  const match = metrics.find((metric) => metric.label === label);
  return match ? String(match.value) : "0";
}

function getSummaryOutputCounts() {
  const counts = (state.lastRunSummary && state.lastRunSummary.outputCounts) || {};
  return {
    refinedRows: Number.isFinite(Number(counts.refinedRows))
      ? Number(counts.refinedRows)
      : Number(metricValue("Refined Rows")),
    invalidRows: Number.isFinite(Number(counts.invalidRows))
      ? Number(counts.invalidRows)
      : Number(metricValue("Invalid")),
    coordinateReviewRows: Number.isFinite(Number(counts.coordinateReviewRows))
      ? Number(counts.coordinateReviewRows)
      : Number(metricValue("Review Needed")),
    rejectedReviewRows: Number.isFinite(Number(counts.rejectedReviewRows))
      ? Number(counts.rejectedReviewRows)
      : Number(metricValue("Excluded Review")),
  };
}

function updateResultsSummary() {
  if (!el.resultsSummaryLine) return;
  if (!state.runId || !state.lastRunSummary) {
    el.resultsSummaryLine.innerHTML = '<span class="summary-pill">Run refinement to create outputs.</span>';
    return;
  }
  const counts = getSummaryOutputCounts();
  const outsideProject = Number(metricValue("Excluded"));
  const reviewCount = counts.coordinateReviewRows;
  el.resultsSummaryLine.innerHTML = `
    <span class="summary-pill">${counts.refinedRows} refined</span>
    <span class="summary-pill">${outsideProject} outside</span>
    <span class="summary-pill">${counts.rejectedReviewRows} excluded</span>
    <span class="summary-pill">${reviewCount} review</span>
  `;
}

function updateReviewStageHeader() {
  if (!el.reviewStageCount || !el.reviewStageTotals) return;
  const visibleSteps = getVisibleReviewSteps();
  const current = getCurrentReviewStep();
  const secondaryCount = (state.reviewSecondaryQueue || []).length;
  const decided = visibleSteps.filter((step) => !!state.reviewDecisions[step.rowKey]).length;
  const total = visibleSteps.length;
  const progress = total ? Math.round((decided / total) * 100) : 0;

  if (!total) {
    if (reviewResultsRecommended()) {
      el.reviewStageCount.textContent = "No likely crash review needed";
      el.reviewStageTotals.textContent = secondaryCount
        ? `${secondaryCount} lower-priority candidate(s) available`
        : "Recommended: continue to results";
    } else {
      el.reviewStageCount.textContent = "Crash review";
      el.reviewStageTotals.textContent = "0 of 0 decided";
    }
    if (el.reviewStageProgressFill) {
      el.reviewStageProgressFill.style.width = "0%";
    }
    return;
  }

  el.reviewStageCount.textContent = current
    ? `Crash ${state.currentReviewIndex + 1} of ${total}`
    : `Crash review (${total})`;
  el.reviewStageTotals.textContent = `${decided} of ${total} decided`;
  if (el.reviewStageProgressFill) {
    el.reviewStageProgressFill.style.width = `${progress}%`;
  }
}

function updateSummary() {
  if (el.summaryData) {
    el.summaryData.textContent = state.dataFile ? state.dataFile.name : "No file selected.";
  }
  if (el.summaryKmz) {
    el.summaryKmz.textContent = state.kmzFile ? state.kmzFile.name : "No boundary selected.";
  }
  if (el.summaryColumns) {
    const lat = el.latColumn.value.trim();
    const lon = el.lonColumn.value.trim();
    el.summaryColumns.textContent = lat && lon ? `${lat} / ${lon}` : "Latitude / Longitude not set.";
  }
  renderStageChrome();
}

function setColumnDetectionBusy(isBusy) {
  if (el.inputShell) {
    el.inputShell.classList.toggle("busy", isBusy);
    el.inputShell.setAttribute("aria-busy", isBusy ? "true" : "false");
  }
  if (el.columnHint) {
    el.columnHint.hidden = isBusy;
  }
  if (el.columnLoadingIndicator) {
    el.columnLoadingIndicator.hidden = !isBusy;
  }
  if (el.latColumn) {
    el.latColumn.disabled = isBusy;
  }
  if (el.lonColumn) {
    el.lonColumn.disabled = isBusy;
  }
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
  const requestId = ++state.headerRequestId;
  const form = new FormData();
  form.append("data_file", file);
  setColumnDetectionBusy(true);
  try {
    const response = await fetch("/api/preview", { method: "POST", body: form });
    if (requestId !== state.headerRequestId || state.dataFile !== file) {
      return;
    }
    if (!response.ok) {
      const data = await response.json().catch(() => ({}));
      if (el.columnHint) {
        el.columnHint.textContent = data.error || "Unable to detect columns.";
      }
      return;
    }

    const data = await response.json();
    const headers = data.headers || [];
    if (headers.length) {
      updateColumnOptions(headers);
      if (el.columnHint) {
        el.columnHint.textContent = `Detected ${headers.length} columns.`;
      }
    } else {
      if (el.columnHint) {
        el.columnHint.textContent = "No columns detected. Enter them manually.";
      }
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
  } finally {
    if (requestId === state.headerRequestId) {
      setColumnDetectionBusy(false);
    }
  }
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
  if (!el.metrics) return;
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
    updateResultsSummary();
    return;
  }
  el.outputLinks.innerHTML = "";
  const describeOutput = (name) => {
    if (/_refined\./i.test(name)) {
      return { title: "Refined crash data", order: 0 };
    }
    if (/Rejected Coordinate Review/i.test(name)) {
      return { title: "Excluded crash review output", order: 2 };
    }
    if (/Coordinate Recovery Review/i.test(name)) {
      return { title: "Coordinate recovery workbook", order: 3 };
    }
    if (/\.kmz$/i.test(name)) {
      return { title: "Crash KMZ", order: 1 };
    }
    if (/Without Valid Lat-Long/i.test(name)) {
      return { title: "Rows missing coordinates", order: 4 };
    }
    if (/\.pdf$/i.test(name)) {
      return { title: "PDF crash report", order: 5 };
    }
    return { title: name, order: 10 };
  };

  outputs
    .map((item) => ({ item, meta: describeOutput(item.name) }))
    .sort((a, b) => a.meta.order - b.meta.order || a.item.name.localeCompare(b.item.name))
    .forEach(({ item, meta }) => {
      const wrapper = document.createElement("div");
      wrapper.className = "output-item";
      wrapper.innerHTML = `
        <div class="output-item-title">${escapeHtml(meta.title)}</div>
        <a href="/api/run/${state.runId}/download/${encodeURIComponent(item.name)}" target="_blank">${escapeHtml(item.name)}</a>
      `;
      el.outputLinks.appendChild(wrapper);
    });
  updateResultsSummary();
}

function setMapPreview(mapName, mapUrl) {
  state.mapReportName = mapName;
  const url = mapUrl || (mapName ? `/api/run/${state.runId}/view/${encodeURIComponent(mapName)}` : null);
  if (!url) {
    previewSurfaces().forEach((surface) => resetPreviewSurface(surface));
    if (el.resultsOpenMap) {
      el.resultsOpenMap.disabled = true;
      delete el.resultsOpenMap.dataset.url;
    }
    return;
  }
  previewSurfaces().forEach((surface) => loadPreviewSurface(surface, url));
  if (el.resultsOpenMap) {
    el.resultsOpenMap.disabled = false;
    el.resultsOpenMap.dataset.url = url;
  }
}

function schedulePreviewMap() {
  if (!state.kmzFile || state.pollTimer) return;
  if (state.previewTimer) {
    window.clearTimeout(state.previewTimer);
  }
  state.previewTimer = window.setTimeout(requestPreviewMap, 300);
}

async function requestPreviewMap() {
  if (!state.kmzFile || state.pollTimer) return;
  const requestId = ++state.previewRequestId;
  previewSurfaces().forEach((surface) => {
    surface.frame.dataset.loaded = "false";
    surface.placeholder.textContent = "Loading map...";
    surface.placeholder.style.display = "flex";
    if (surface.button) {
      surface.button.disabled = true;
    }
  });

  const form = new FormData();
  form.append("boundary_file", state.kmzFile);
  const latColumn = el.latColumn.value.trim();
  const lonColumn = el.lonColumn.value.trim();
  const includeCrashData = !!(state.dataFile && latColumn && lonColumn);
  if (includeCrashData) {
    form.append("data_file", state.dataFile);
    form.append("lat_column", latColumn);
    form.append("lon_column", lonColumn);
  }

  const response = await fetch("/api/preview-map", { method: "POST", body: form });
  if (requestId !== state.previewRequestId) return;
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    previewSurfaces().forEach((surface) => {
      surface.frame.dataset.loaded = "false";
      surface.placeholder.textContent = data.error || "Map preview unavailable.";
      surface.placeholder.style.display = "flex";
      if (surface.button) {
        surface.button.disabled = true;
        delete surface.button.dataset.url;
      }
    });
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

function buildRelabelFormData() {
  const form = new FormData();
  form.append(
    "label_order",
    (el.resultsLabelOrder && el.resultsLabelOrder.value) || el.labelOrder.value || "auto"
  );
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
    excluded: 0,
  };
  Object.values(state.reviewDecisions).forEach((decision) => {
    if (decision.action === "reject") {
      stats.excluded += 1;
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
  el.mapSubtitle.textContent = "Preview the project boundary and current outputs.";
  el.wizardMap.hidden = true;
  el.mapFrame.style.display = "block";
  el.wizardMapToolbar.hidden = true;
  el.clearMapSelection.disabled = true;
  if (el.mapFrame.getAttribute("src") && el.mapFrame.dataset.loaded === "true") {
    el.mapPlaceholder.style.display = "none";
  } else {
    el.mapPlaceholder.style.display = "flex";
  }
}

function renderReviewMap() {
  const current = getCurrentReviewStep();
  const polygon = state.reviewMapData && Array.isArray(state.reviewMapData.polygon)
    ? state.reviewMapData.polygon
    : [];
  if (!current || !state.reviewMapData || !window.L || !polygon.length) {
    showProjectPreviewMap();
    return;
  }

  const drawMap = () => {
    const hasUsableSuggestedPoint = current.hasSuggestion && current.suggestedInsideBoundary !== false;
    ensureReviewMap();
    if (!state.reviewMap || !state.reviewMapLayers) {
      showProjectPreviewMap();
      return;
    }

    el.mapMode.textContent = "Review Wizard";
    el.mapSubtitle.textContent = `Crash ${state.currentReviewIndex + 1} of ${getVisibleReviewSteps().length}`;
    el.mapFrame.style.display = "none";
    el.wizardMap.hidden = false;
    el.mapPlaceholder.style.display = "none";
    el.wizardMapToolbar.hidden = false;

    window.setTimeout(() => {
      try {
        if (state.reviewMap) {
          state.reviewMap.invalidateSize();
        }
      } catch (error) {
        console.error("Review map resize failed.", error);
      }
    }, 0);

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
      } else if (hasUsableSuggestedPoint) {
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

    if (hasUsableSuggestedPoint) {
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
      } else if (hasUsableSuggestedPoint) {
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
      el.wizardMapSelection.textContent = "Pick mode active";
    } else if (draftPlacement) {
      el.wizardMapSelection.textContent = insideDraft
        ? `Pin staged: ${formatCoordinate(draftPlacement.latitude)}, ${formatCoordinate(draftPlacement.longitude)}`
        : "Pin staged outside boundary";
    } else if (decision && decision.action === "reject") {
      el.wizardMapSelection.textContent = "Excluded";
    } else if (decision && decision.action === "apply" && decision.placementMode === "manual") {
      el.wizardMapSelection.textContent = `Placed: ${formatCoordinate(decision.latitude)}, ${formatCoordinate(decision.longitude)}`;
    } else if (decision && decision.action === "apply") {
      el.wizardMapSelection.textContent = `Using suggested point`;
    } else if (hasUsableSuggestedPoint) {
      el.wizardMapSelection.textContent = "Suggested point available";
    } else {
      el.wizardMapSelection.textContent = "No suggested point";
    }
    el.clearMapSelection.textContent = "Discard Map Pin";
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

function getCurrentChoiceState(step) {
  if (!step) {
    return {
      kind: "none",
      statusClass: "",
      statusText: "Pending",
      helperText: "",
      actionLabel: "",
      showAction: false,
    };
  }

  const decision = state.reviewDecisions[step.rowKey];
  const draftPlacement = getDraftPlacement(step);
  const draftInside = draftPlacement
    ? pointInProjectBoundary(draftPlacement.latitude, draftPlacement.longitude)
    : false;

  if (decision && decision.action === "reject") {
    return {
      kind: "excluded",
      statusClass: "status-excluded",
      statusText: "Excluded",
      helperText: "",
      actionLabel: "Undo",
      showAction: true,
    };
  }

  if (decision && decision.action === "apply") {
    const placementLabel = decision.placementMode === "manual"
      ? "your map placement"
      : "the suggested placement";
    return {
      kind: "included",
      statusClass: "status-included",
      statusText: `Included at ${formatCoordinate(decision.latitude)}, ${formatCoordinate(decision.longitude)}`,
      helperText: placementLabel,
      actionLabel: "Undo",
      showAction: true,
    };
  }

  if (draftPlacement) {
    const coordinateText = `${formatCoordinate(draftPlacement.latitude)}, ${formatCoordinate(draftPlacement.longitude)}`;
    return {
      kind: "staged",
      statusClass: "status-staged",
      statusText: draftInside
        ? `Pin staged at ${coordinateText}`
        : `Pin outside boundary`,
      helperText: "",
      actionLabel: "Clear pin",
      showAction: true,
    };
  }

  return {
    kind: "undecided",
    statusClass: "",
    statusText: "Pending",
    helperText: "",
    actionLabel: "",
    showAction: false,
  };
}

function renderReviewQueue() {
  const primarySteps = state.reviewQueue || [];
  const secondarySteps = state.reviewSecondaryQueue || [];
  const visibleSteps = getVisibleReviewSteps();
  const totalLoaded = primarySteps.length + secondarySteps.length;
  const recommendResults = reviewResultsRecommended();

  if (el.reviewQueueSubtitle) {
    const decidedCount = visibleSteps.filter((step) => !!state.reviewDecisions[step.rowKey]).length;
    if (recommendResults) {
      el.reviewQueueSubtitle.textContent = "Recommended: continue to results.";
    } else {
      el.reviewQueueSubtitle.textContent = totalLoaded
        ? `${decidedCount} of ${visibleSteps.length || totalLoaded} decided`
        : "Work left: none";
    }
  }

  if (!totalLoaded) {
    state.showSecondaryReview = false;
    state.currentReviewIndex = 0;
    state.reviewMapPickMode = false;
    state.reviewExcludeConfirmRow = null;
    setReviewWorkbenchTab("map");
    el.reviewSummary.textContent = state.runId
      ? "No crashes without lat/long data were flagged as likely inside the project boundary. Continue to results to generate refined outputs."
      : "No review items loaded.";
    el.reviewList.className = "review-list empty";
    el.reviewList.innerHTML = state.runId
      ? `
        <section class="wizard-empty review-empty-callout">
          <div class="review-empty-kicker">Recommended next step</div>
          <div class="review-section-title">No likely crash review needed</div>
          <div class="review-section-subtitle">No crashes without lat/long data were likely inside the project boundary. Continue to results to generate the refined outputs.</div>
          <div class="review-empty-actions">
            <button class="btn primary" data-action="continue-results">Continue to results</button>
          </div>
        </section>
      `
      : "Run refinement to start review.";
    renderReviewMap();
    updateReviewStageHeader();
    updateStageAvailability();
    updateBrowserReviewButton();
    return;
  }

  const hiddenSecondaryText = secondarySteps.length && !state.showSecondaryReview
    ? `${secondarySteps.length} lower-priority hidden`
    : "";
  const decidedVisible = visibleSteps.filter((step) => !!state.reviewDecisions[step.rowKey]).length;
  if (recommendResults) {
    el.reviewSummary.textContent = "No crashes without lat/long data were flagged as likely inside the project boundary. Continue to results to generate refined outputs, or open the lower-priority candidates if you want an extra pass.";
  } else {
    el.reviewSummary.textContent = `${decidedVisible} of ${visibleSteps.length} decided${hiddenSecondaryText ? ` • ${hiddenSecondaryText}` : ""}`;
  }

  el.reviewList.className = "review-list wizard-mode";
  el.reviewList.innerHTML = "";

  if (!visibleSteps.length) {
    el.reviewList.innerHTML = `
      <section class="wizard-empty review-empty-callout">
        <div class="review-empty-kicker">Recommended next step</div>
        <div class="review-section-title">No likely crash review needed</div>
        <div class="review-section-subtitle">No crashes without lat/long data were flagged as likely inside the project boundary. Continue to results to generate the refined outputs, or open the lower-priority candidates if you want an extra pass.</div>
        <div class="review-empty-actions">
          <button class="btn primary" data-action="continue-results">Continue to results</button>
          ${secondarySteps.length ? `<button class="btn secondary small" data-action="toggle-secondary">Review lower-priority candidates</button>` : ""}
        </div>
      </section>
    `;
    state.reviewExcludeConfirmRow = null;
    renderReviewMap();
    updateReviewStageHeader();
    updateStageAvailability();
    updateBrowserReviewButton();
    return;
  }

  const current = getCurrentReviewStep();
  if (!current) {
    renderReviewMap();
    updateReviewStageHeader();
    updateStageAvailability();
    updateBrowserReviewButton();
    return;
  }

  const decision = state.reviewDecisions[current.rowKey];
  const reviewBucket = current.reviewBucket === "secondary" ? "secondary" : "primary";
  const bucketLabel = reviewBucket === "secondary" ? "Lower priority" : "Likely in project";
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
  const choiceState = getCurrentChoiceState(current);
  const hasUsableSuggestedPoint = current.hasSuggestion && current.suggestedInsideBoundary !== false;
  const canAcceptSuggested = hasUsableSuggestedPoint;
  const navigationSecondaryLabel = secondarySteps.length
    ? (state.showSecondaryReview ? "Hide Lower-Likelihood Crashes" : "Load Lower-Likelihood Crashes")
    : "";
  const currentChoiceAction = choiceState.showAction
    ? `<button class="btn secondary small" data-action="wizard-clear-decision" data-row="${escapeHtml(current.rowKey)}">${escapeHtml(choiceState.actionLabel)}</button>`
    : "";
  const metadataChips = metadata.length
    ? metadata.map((item) => `<span class="meta-chip">${escapeHtml(item)}</span>`).join("")
    : '<span class="meta-chip">No crash metadata</span>';
  const reviewNote = current.reviewReason || current.note || "No review signal recorded.";
  const detailSummary = current.detail || "Location details unavailable.";
  const suggestionBadge = hasUsableSuggestedPoint
    ? `Suggested ${escapeHtml(`${formatCoordinate(current.suggestedLatitude)}, ${formatCoordinate(current.suggestedLongitude)}`)}`
    : "No suggestion";
  const extraDetails = reviewDetails.length || current.note || current.hasNarrative
    ? `
      <details class="review-more compact">
        <summary>Details</summary>
        ${reviewDetails.length ? `<ul class="review-relevance-list">${reviewDetails.map((line) => `<li>${escapeHtml(line)}</li>`).join("")}</ul>` : ""}
        ${current.note ? `<div class="review-note">${escapeHtml(current.note)}</div>` : ""}
        ${current.hasNarrative ? `<div class="wizard-narrative-text">${escapeHtmlWithBreaks(current.narrative)}</div>` : ""}
      </details>
    `
    : "";

  el.reviewList.innerHTML = `
    <section class="wizard-card ${decision ? "selected" : ""}">
      <div class="wizard-progress compact">
        <div class="wizard-step-index">Crash ${state.currentReviewIndex + 1} of ${visibleSteps.length}</div>
        <div class="wizard-step-meta wizard-chip-row">${metadataChips}</div>
      </div>
      <div class="review-head">
        <div>
          <div class="review-title">${escapeHtml(current.title)}</div>
          <div class="review-detail">${escapeHtml(current.detail || "Location details unavailable.")}</div>
        </div>
        <div class="review-badges compact-stack">
          <span class="review-badge ${reviewBucket}">${escapeHtml(bucketLabel)}</span>
          <span class="review-badge status ${escapeHtml(choiceState.statusClass)}">${escapeHtml(choiceState.statusText)}</span>
        </div>
      </div>
      <div class="wizard-chip-row">
        <span class="meta-chip">${escapeHtml(suggestionBadge)}</span>
        ${draftPlacement ? `<span class="meta-chip ${draftInside ? "ready" : "warn"}">Pin ${escapeHtml(`${formatCoordinate(draftPlacement.latitude)}, ${formatCoordinate(draftPlacement.longitude)}`)}</span>` : ""}
      </div>
      <div class="review-relevance compact">
        <div class="review-relevance-summary">${escapeHtml(reviewNote)}</div>
        <div class="review-note">${escapeHtml(detailSummary)}</div>
        ${extraDetails}
      </div>
      <div class="wizard-actions compact">
        <button class="btn secondary small" data-action="wizard-accept-suggested" data-row="${escapeHtml(current.rowKey)}"${canAcceptSuggested ? "" : " disabled"}>Use suggested</button>
        <button class="btn secondary small" data-action="wizard-pick-map" data-row="${escapeHtml(current.rowKey)}">${state.reviewMapPickMode ? "Picking on map" : "Place on map"}</button>
        <button class="btn secondary small" data-action="wizard-confirm-manual" data-row="${escapeHtml(current.rowKey)}"${draftPlacement && draftInside ? "" : " disabled"}>Confirm pin</button>
        <button class="btn danger small" data-action="wizard-exclude" data-row="${escapeHtml(current.rowKey)}">Exclude</button>
        ${currentChoiceAction}
      </div>
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
  updateReviewStageHeader();
  updateStageAvailability();
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
    state.reviewExcludeConfirmRow = null;
    setReviewWorkbenchTab("map");
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
    state.reviewExcludeConfirmRow = null;
    setReviewWorkbenchTab("map");
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
  state.reviewExcludeConfirmRow = null;
  setReviewWorkbenchTab("map");
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
  clearPendingExclusion();
  delete state.reviewDraftPlacements[rowKey];
  state.reviewMapPickMode = false;
  state.reviewMapFocusKey = null;
  state.reviewDecisions[rowKey] = {
    rowKey,
    latitude: step.suggestedLatitude,
    longitude: step.suggestedLongitude,
    action: "apply",
    placementMode: "suggested",
    note: "Confirmed suggested placement in browser review workbench.",
  };
  moveToNextReviewStep(true);
  renderReviewQueue();
}

function beginMapPlacement(rowKey) {
  const current = getCurrentReviewStep();
  const togglingCurrentStep = current && current.rowKey === rowKey && state.reviewMapPickMode;
  focusReviewStep(rowKey);
  clearPendingExclusion();
  state.reviewMapPickMode = !togglingCurrentStep;
  state.reviewMapFocusKey = null;
  if (state.reviewMapPickMode && isReviewWorkbenchTabbed()) {
    setReviewWorkbenchTab("map");
  }
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
  clearPendingExclusion();
  state.reviewMapPickMode = false;
  state.reviewMapFocusKey = null;
  state.reviewDecisions[rowKey] = {
    rowKey,
    latitude: draftPlacement.latitude,
    longitude: draftPlacement.longitude,
    action: "apply",
    placementMode: "manual",
    note: "Confirmed manual map placement in browser review workbench.",
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
  clearPendingExclusion();
  delete state.reviewDraftPlacements[rowKey];
  state.reviewMapPickMode = false;
  state.reviewMapFocusKey = null;
  state.reviewDecisions[rowKey] = {
    rowKey,
    action: "reject",
    note: "Excluded from project in browser review workbench.",
  };
  moveToNextReviewStep(true);
  renderReviewQueue();
}

function toggleCrashExclusion(rowKey) {
  rejectReviewCrash(rowKey);
}

function clearReviewDecision(rowKey) {
  clearPendingExclusion();
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
  clearPendingExclusion();
  delete state.reviewDraftPlacements[current.rowKey];
  state.reviewMapPickMode = false;
  state.reviewMapFocusKey = null;
  renderReviewQueue();
}

async function startRun() {
  if (!state.dataFile || !state.kmzFile) return;
  clearLogs();
  state.runInputs = {
    dataFile: state.dataFile.name,
    kmzFile: state.kmzFile.name,
    latColumn: el.latColumn.value.trim(),
    lonColumn: el.lonColumn.value.trim(),
    labelOrder: el.labelOrder.value || "auto",
  };
  state.reviewQueue = [];
  state.reviewSecondaryQueue = [];
  state.reviewDecisions = {};
  state.reviewDraftPlacements = {};
  state.currentReviewIndex = 0;
  state.showSecondaryReview = false;
  state.reviewMapData = null;
  state.reviewMapPickMode = false;
  state.reviewMapFocusKey = null;
  state.reviewExcludeConfirmRow = null;
  setReviewWorkbenchTab("map");
  renderReviewQueue();
  setUiStage("inputs", { persist: false });
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
  setUiStage("results", { persist: false });
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
  setUiStage("results", { persist: false });
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
  state.reviewExcludeConfirmRow = null;
  setReviewWorkbenchTab("map");
  renderReviewQueue();
  el.reviewInput.value = "";
  el.reviewLabel.textContent = "Reviewed coordinate workbook";
  el.reviewHint.textContent = "Upload a reviewed workbook";
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
  setUiStage("results", { persist: false });
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
  state.reviewExcludeConfirmRow = null;
  setReviewWorkbenchTab("map");
  renderReviewQueue();
  state.runId = data.runId;
  state.logSeq = 0;
  pollLogs();
  state.pollTimer = window.setInterval(pollLogs, 1200);
}

async function startRelabel() {
  if (!state.runId) {
    showToast("Run refinement first.");
    return;
  }
  clearLogs();
  setUiStage("results", { persist: false });
  setStatus("running", "Regenerating labels", "Updating the refined spreadsheet and KMZ numbering.");
  setProgressRunning(true);
  setReportProgressRunning(false);
  el.runRefine.disabled = true;
  el.generateReport.disabled = true;
  el.applyReview.disabled = true;
  el.applyBrowserReview.disabled = true;
  if (el.resultsRelabel) {
    el.resultsRelabel.disabled = true;
  }
  el.snapshotTag.textContent = "Running";
  el.snapshotStatus.textContent = "Regenerating KMZ labels.";
  el.outputLinks.textContent = "Relabel in progress...";

  const response = await fetch(`/api/run/${state.runId}/relabel`, {
    method: "POST",
    body: buildRelabelFormData(),
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    showToast(data.error || "Unable to regenerate labels.");
    setStatus("error", "Label regeneration failed", "Check the requested direction and try again.");
    setProgressRunning(false);
    updateRunButton();
    return;
  }
  pollLogs();
  if (!state.pollTimer) {
    state.pollTimer = window.setInterval(pollLogs, 1200);
  }
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
  state.runInputs = data.inputs || state.runInputs;
  state.lastRunSummary = data.summary || null;
  state.lastOutputs = data.outputs || [];
  setLabelOrderSelection((state.runInputs && state.runInputs.labelOrder) || "auto", { scope: "results" });
  const runKind = (data.inputs && data.inputs.runKind) || "refine";
  const usedReviewWorkbook = !!(
    data.inputs && (data.inputs.coordinateReviewFile || data.inputs.browserReviewDecisionCount)
  );
  if (status === "success") {
    const successTitle = runKind === "report"
      ? "Report complete"
      : (runKind === "relabel"
        ? "Labels regenerated"
        : (usedReviewWorkbook ? "Review decisions applied" : "Refinement complete"));
    const successSnapshot = runKind === "report"
      ? "PDF report completed successfully."
      : (runKind === "relabel"
        ? "Refined output and KMZ labels were updated."
        : (usedReviewWorkbook
          ? "Refinement reran with approved coordinates."
          : "Refinement completed successfully."));
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
      : (runKind === "relabel"
        ? "Label regeneration failed"
        : (usedReviewWorkbook ? "Review apply failed" : "Refinement failed"));
    const errorSnapshot = runKind === "report"
      ? "PDF report encountered errors."
      : (runKind === "relabel"
        ? "Relabeling encountered errors."
        : (usedReviewWorkbook
          ? "Approved coordinate rerun encountered errors."
          : "Refinement encountered errors."));
    const errorToast = runKind === "report"
      ? "PDF report failed."
      : (runKind === "relabel"
        ? "Regenerating labels failed."
        : (usedReviewWorkbook ? "Applying review decisions failed." : "Refinement failed."));
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
  } else {
    setMapPreview(null);
  }
  if (status === "success") {
    await fetchReviewQueue(state.runId);
  } else {
    renderReviewQueue();
  }

  if (status === "success") {
    if (runKind === "refine" && !usedReviewWorkbook && reviewPendingCount()) {
      setUiStage("review", { persist: false });
    } else {
      setUiStage("results", { persist: false });
    }
  }

  const finishedAt = data.finishedAt;
  if (finishedAt) {
    el.snapshotLastRun.textContent = `Completed ${new Date(finishedAt).toLocaleString()}`;
  }
  setProgressRunning(false);
  setReportProgressRunning(false);
  updateRunButton();
  updateStageAvailability();
  updateResultsSummary();
  updateLabelOrderControls();
  renderStageChrome();
  saveUiSession();
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

async function restoreUiSession() {
  state.isRestoringSession = true;
  const saved = readUiSession();
  if (!saved || !saved.runId) {
    updateStageAvailability();
    renderStageChrome();
    state.isRestoringSession = false;
    state.isBootstrappingUi = false;
    saveUiSession();
    return;
  }

  try {
    const response = await fetch(`/api/run/${saved.runId}`);
    if (!response.ok) {
      clearUiSession();
      renderStageChrome();
      state.isRestoringSession = false;
      state.isBootstrappingUi = false;
      return;
    }

    const data = await response.json();
    state.runId = saved.runId;
    state.runInputs = data.inputs || saved.runInputs || null;
    state.lastRunSummary = data.summary || saved.lastRunSummary || null;
    state.lastOutputs = data.outputs || saved.lastOutputs || [];
    setLabelOrderSelection((state.runInputs && state.runInputs.labelOrder) || "auto", { scope: "results" });
    renderOutputs(state.lastOutputs);
    renderMetrics(state.lastRunSummary || {});
    if (data.summary && data.summary.mapReport) {
      setMapPreview(data.summary.mapReport);
    }
    if (data.finishedAt) {
      el.snapshotLastRun.textContent = `Completed ${new Date(data.finishedAt).toLocaleString()}`;
    }

    await fetchReviewQueue(state.runId);
    const validKeys = new Set(getAllReviewSteps().map((step) => step.rowKey));
    if (saved.reviewDecisions && typeof saved.reviewDecisions === "object") {
      state.reviewDecisions = Object.fromEntries(
        Object.entries(saved.reviewDecisions).filter(([key]) => validKeys.has(key))
      );
    }
    if (saved.reviewDraftPlacements && typeof saved.reviewDraftPlacements === "object") {
      state.reviewDraftPlacements = Object.fromEntries(
        Object.entries(saved.reviewDraftPlacements).filter(([key]) => validKeys.has(key))
      );
    }
    state.currentReviewIndex = Number.isInteger(saved.currentReviewIndex) ? saved.currentReviewIndex : 0;
    state.showSecondaryReview = !!saved.showSecondaryReview;
    state.reviewExcludeConfirmRow = null;
    setReviewWorkbenchTab(saved.reviewWorkbenchTab || "map");
    renderReviewQueue();

    const savedStage = saved.uiStage || "inputs";
    if (savedStage === "review" && reviewPendingCount()) {
      setUiStage("review", { persist: false });
    } else if (savedStage === "results" && state.runId) {
      setUiStage("results", { persist: false });
    } else {
      setUiStage("inputs", { persist: false });
    }
    if (data.status === "running") {
      const runKind = (data.inputs && data.inputs.runKind) || "refine";
      const runningTitle = runKind === "report"
        ? "Report running"
        : (runKind === "relabel"
          ? "Regenerating labels"
          : (runKind === "review_apply" ? "Applying review decisions" : "Refinement running"));
      setStatus("running", runningTitle, data.message || "Run in progress.");
      el.snapshotTag.textContent = "Running";
      el.snapshotStatus.textContent = data.message || "Run in progress.";
      setProgressRunning(true);
      setReportProgressRunning(runKind === "report");
      state.logSeq = 0;
      pollLogs();
      if (!state.pollTimer) {
        state.pollTimer = window.setInterval(pollLogs, 1200);
      }
    } else {
      setProgressRunning(false);
      setReportProgressRunning(false);
    }
    setAdvancedToolsOpen(!!saved.advancedToolsOpen);
    setTechnicalDetailsOpen(!!saved.detailsPanelOpen);
    updateStageAvailability();
    updateRunButton();
    updateLabelOrderControls();
    renderStageChrome();
  } catch (_error) {
    clearUiSession();
    setUiStage("inputs", { persist: false });
    renderStageChrome();
  } finally {
    state.isRestoringSession = false;
    state.isBootstrappingUi = false;
    saveUiSession();
  }
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
  el.labelOrder.addEventListener("change", () => {
    setLabelOrderSelection(el.labelOrder.value, { scope: "input" });
    saveUiSession();
  });
  if (el.resultsLabelOrder) {
    el.resultsLabelOrder.addEventListener("change", () => {
      setLabelOrderSelection(el.resultsLabelOrder.value, { scope: "results" });
      saveUiSession();
    });
  }
  if (el.resultsGenerateReport) {
    el.resultsGenerateReport.addEventListener("click", startReport);
  }
  if (el.resultsRelabel) {
    el.resultsRelabel.addEventListener("click", startRelabel);
  }
  el.applyReview.addEventListener("click", startApplyReview);
  el.applyBrowserReview.addEventListener("click", startApplyBrowserReview);
  if (el.reviewSkipToResults) {
    el.reviewSkipToResults.addEventListener("click", () => setUiStage("results"));
  }
  if (el.resultsResumeReview) {
    el.resultsResumeReview.addEventListener("click", () => setUiStage("review"));
  }
  [el.stageStepInputs, el.stageStepReview, el.stageStepResults].forEach((button) => {
    if (!button) return;
    button.addEventListener("click", () => {
      const targetStage = button.dataset.stageTarget;
      if (!targetStage || button.disabled) return;
      setUiStage(targetStage);
    });
  });
  el.reviewList.addEventListener("click", (event) => {
    const target = event.target.closest("[data-action]");
    if (!target) return;
    if (target.dataset.action === "continue-results") {
      setUiStage("results");
      return;
    }
    if (target.dataset.action === "toggle-secondary") {
      state.showSecondaryReview = !state.showSecondaryReview;
      state.reviewMapPickMode = false;
      state.reviewMapFocusKey = null;
      clearPendingExclusion();
      renderReviewQueue();
      return;
    }
    if (target.dataset.action === "wizard-prev") {
      state.reviewMapPickMode = false;
      moveToPreviousReviewStep();
      state.reviewMapFocusKey = null;
      clearPendingExclusion();
      renderReviewQueue();
      return;
    }
    if (target.dataset.action === "wizard-next") {
      state.reviewMapPickMode = false;
      moveToNextReviewStep();
      state.reviewMapFocusKey = null;
      clearPendingExclusion();
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
    if (target.dataset.action === "wizard-exclude") {
      toggleCrashExclusion(rowKey);
      return;
    }
    if (target.dataset.action === "wizard-clear-decision") {
      clearReviewDecision(rowKey);
    }
  });
  el.clearMapSelection.addEventListener("click", clearCurrentMapPlacement);
  document.querySelectorAll("[data-review-tab]").forEach((button) => {
    button.addEventListener("click", () => {
      setReviewWorkbenchTab(button.dataset.reviewTab);
      saveUiSession();
    });
  });
  if (el.advancedToolsPanel) {
    el.advancedToolsPanel.addEventListener("toggle", () => {
      state.advancedToolsOpen = el.advancedToolsPanel.open;
      saveUiSession();
    });
  }
  if (el.technicalDetails) {
    el.technicalDetails.addEventListener("toggle", () => {
      state.detailsPanelOpen = el.technicalDetails.open;
      saveUiSession();
    });
  }
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
    state.runInputs = null;
    state.lastRunSummary = null;
    state.lastOutputs = [];
    state.reviewQueue = [];
    state.reviewSecondaryQueue = [];
    state.reviewDecisions = {};
    state.reviewDraftPlacements = {};
    state.currentReviewIndex = 0;
    state.showSecondaryReview = false;
    state.reviewMapData = null;
    state.reviewMapPickMode = false;
    state.reviewMapFocusKey = null;
    state.reviewExcludeConfirmRow = null;
    state.reviewWorkbenchTab = "details";
    state.uiStage = "inputs";
    state.advancedToolsOpen = false;
    state.detailsPanelOpen = false;
    el.dataInput.value = "";
    el.kmzInput.value = "";
    el.pdfInput.value = "";
    el.reviewInput.value = "";
    el.latColumn.value = "";
    el.lonColumn.value = "";
    el.labelOrder.selectedIndex = 0;
    if (el.resultsLabelOrder) {
      el.resultsLabelOrder.selectedIndex = 0;
    }
    el.dataLabel.textContent = "Crash spreadsheet (.csv, .xlsx)";
    el.dataHint.textContent = "Drop file or click to browse";
    el.kmzLabel.textContent = "Boundary KMZ (.kmz)";
    el.kmzHint.textContent = "One polygon only";
    el.pdfLabel.textContent = "Alternate PDF source (.csv, .xlsx)";
    el.pdfHint.textContent = "Optional";
    el.reviewLabel.textContent = "Reviewed coordinate workbook";
    el.reviewHint.textContent = "Upload a reviewed workbook";
    updateColumnOptions([]);
    setStatus("idle", "Ready to run", "Add crash data, boundary, and columns.");
    setProgressRunning(false);
    el.snapshotTag.textContent = "Idle";
    el.snapshotStatus.textContent = "Waiting for inputs.";
    el.snapshotLastRun.textContent = "No runs yet.";
    el.outputLinks.textContent = "No outputs yet.";
    if (el.resultsSummaryLine) {
      el.resultsSummaryLine.innerHTML = '<span class="summary-pill">Run refinement to create outputs.</span>';
    }
    if (el.metrics) {
      el.metrics.innerHTML = "";
    }
    el.mapPlaceholder.textContent = "The map appears here once files are loaded.";
    setMapPreview(null);
    renderReviewQueue();
    setReportProgressRunning(false);
    setReviewWorkbenchTab("map");
    setUiStage("inputs", { persist: false });
    setAdvancedToolsOpen(false);
    setTechnicalDetailsOpen(false);
    updateSummary();
    updateRunButton();
    clearUiSession();
  });
  el.popLog.addEventListener("click", openLogWindow);
  [el.inputOpenMap, el.openMap, el.resultsOpenMap].forEach((button) => button && button.addEventListener("click", () => {
    const url = button.dataset.url || (el.openMap && el.openMap.dataset.url);
    if (url) window.open(url, "_blank");
  }));
}

function wireModals() {
  if (el.openGuide && el.guideModal) {
    el.openGuide.addEventListener("click", () => el.guideModal.showModal());
  }
  if (el.openNotes && el.notesModal) {
    el.openNotes.addEventListener("click", () => el.notesModal.showModal());
  }
  document.querySelectorAll("[data-close]").forEach((button) => {
    button.addEventListener("click", () => {
      const dialog = button.closest("dialog");
      if (dialog) dialog.close();
    });
  });
}

function bindReviewShortcuts() {
  document.addEventListener("keydown", (event) => {
    const activeTag = document.activeElement && document.activeElement.tagName;
    const isTyping = activeTag === "INPUT" || activeTag === "TEXTAREA" || activeTag === "SELECT";
    if (isTyping || state.uiStage !== "review") {
      return;
    }

    const current = getCurrentReviewStep();
    if (!current) {
      return;
    }

    if (event.key === "ArrowLeft") {
      event.preventDefault();
      moveToPreviousReviewStep();
      state.reviewMapPickMode = false;
      state.reviewMapFocusKey = null;
      renderReviewQueue();
      return;
    }
    if (event.key === "ArrowRight") {
      event.preventDefault();
      moveToNextReviewStep();
      state.reviewMapPickMode = false;
      state.reviewMapFocusKey = null;
      renderReviewQueue();
      return;
    }

    const key = event.key.toLowerCase();
    if (key === "a" && current.hasSuggestion && current.suggestedInsideBoundary !== false) {
      event.preventDefault();
      confirmSuggestedPlacement(current.rowKey);
      return;
    }
    if (key === "p") {
      event.preventDefault();
      beginMapPlacement(current.rowKey);
      return;
    }
    if (key === "x") {
      event.preventDefault();
      rejectReviewCrash(current.rowKey);
    }
  });
}

function init() {
  resetTransientInputUi();
  previewSurfaces().forEach((surface) => bindPreviewSurface(surface.frame, surface.placeholder));
  wireModals();
  bindReviewShortcuts();
  bindInputs();
  setupDropZone(el.dataDrop, el.dataInput, (file) => {
    if (!validateDataFile(file)) {
      showToast("Crash data must be a CSV or Excel file.");
      return;
    }
    state.dataFile = file;
    setUiStage("inputs", { persist: false });
    el.latColumn.value = "";
    el.lonColumn.value = "";
    el.dataLabel.textContent = file.name;
    el.dataHint.textContent = "Ready";
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
    setUiStage("inputs", { persist: false });
    el.kmzLabel.textContent = file.name;
    el.kmzHint.textContent = "Ready";
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
    setAdvancedToolsOpen(true);
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
    setAdvancedToolsOpen(true);
    el.reviewLabel.textContent = file.name;
    el.reviewHint.textContent = "Ready";
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
  setReviewWorkbenchTab("map");
  setLabelOrderSelection("auto");
  setUiStage("inputs", { persist: false });
  setAdvancedToolsOpen(false);
  setTechnicalDetailsOpen(false);
  restoreUiSession();
}

init();
