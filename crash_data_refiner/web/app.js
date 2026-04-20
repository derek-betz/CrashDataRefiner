const state = {
  dataFile: null,
  kmzFile: null,
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
  reviewMapPreserveView: false,
  reviewMapPendingView: null,
  reviewMapFeedbackTimer: null,
  reviewMapFeedbackFadeTimer: null,
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
  previewMapUrl: null,
  previewTimer: null,
  previewRequestId: 0,
  headerRequestId: 0,
  coneGuy: {
    milestone: "load",
    progress: 10,
    driveTimer: null,
    settleTimer: null,
    calcCycleTimer: null,
    calcSignature: "",
  },
  toastTimer: null,
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
  applyReview: document.getElementById("apply-review"),
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
  workflowFocus: document.getElementById("workflow-focus"),
  workflowWarning: document.getElementById("workflow-warning"),
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
  centerSuggestedPoint: document.getElementById("center-suggested-point"),
  wizardMap: document.getElementById("wizard-map"),
  reviewMapFeedback: document.getElementById("review-map-feedback"),
  reviewMapFeedbackBubble: document.getElementById("review-map-feedback-bubble"),
  wizardMapToolbar: document.getElementById("wizard-map-toolbar"),
  wizardMapContext: document.getElementById("wizard-map-context"),
  wizardMapSelection: document.getElementById("wizard-map-selection"),
  wizardMapShortcuts: document.getElementById("wizard-map-shortcuts"),
  clearMapSelection: document.getElementById("clear-map-selection"),
  inputOpenMap: document.getElementById("input-open-map"),
  openMap: document.getElementById("open-map"),
  reviewList: document.getElementById("review-list"),
  reviewSummary: document.getElementById("review-summary"),
  reviewQueueSubtitle: document.getElementById("review-queue-subtitle"),
  reviewQueueExplainer: document.getElementById("review-queue-explainer"),
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
  coneTracker: document.getElementById("cone-tracker"),
  coneTrackerState: document.getElementById("cone-tracker-state"),
  coneTrackerProgress: document.getElementById("cone-tracker-progress"),
  coneTrackerNote: document.getElementById("cone-tracker-note"),
  coneTrackerGuidance: document.getElementById("cone-tracker-guidance"),
  coneTrackerCalcScreen: document.querySelector(".cone-tracker-calculator-screen"),
  coneTrackerNodes: Array.from(document.querySelectorAll("[data-cone-node]")),
};

const SESSION_KEY = "crash-data-refiner-ui-state-v2";
const LEGACY_SESSION_KEYS = ["crash-data-refiner-ui-state"];
const UI_BUSY_CONTROLS = [
  "runRefine",
  "applyReview",
  "applyBrowserReview",
  "resultsRelabel",
  "labelOrder",
  "resultsLabelOrder",
  "stageStepInputs",
  "stageStepReview",
  "stageStepResults",
];

async function parseJsonSafe(response) {
  try {
    return await response.json();
  } catch (_error) {
    return {};
  }
}

function clearPollingTimer() {
  if (!state.pollTimer) return;
  window.clearInterval(state.pollTimer);
  state.pollTimer = null;
}

function setUiBusy(isBusy) {
  UI_BUSY_CONTROLS.forEach((key) => {
    const control = el[key];
    if (!control) return;
    if (isBusy) {
      control.dataset.busyDisabled = control.disabled ? "true" : "false";
      control.disabled = true;
      return;
    }
    if (control.dataset.busyDisabled === "true") {
      control.disabled = true;
    }
    delete control.dataset.busyDisabled;
  });
}

function unlockUiAfterRun() {
  setUiBusy(false);
  updateRunButton();
  updateReviewButton();
  updateRelabelButton();
  updateStageAvailability();
  updateLabelOrderControls();
}

function handleRunConnectionFailure(
  title,
  detail,
  toastMessage,
  { clearSession = false } = {}
) {
  clearPollingTimer();
  setProgressRunning(false);
  setStatus("error", title, detail);
  el.snapshotTag.textContent = "Failed";
  el.snapshotStatus.textContent = detail;
  updateConeTracker("error");
  if (clearSession) {
    state.runId = null;
    clearUiSession();
  }
  showToast(toastMessage);
  unlockUiAfterRun();
}

function showToast(message) {
  if (state.toastTimer) {
    window.clearTimeout(state.toastTimer);
    state.toastTimer = null;
  }
  el.toast.textContent = message;
  el.toast.classList.add("show");
  state.toastTimer = window.setTimeout(() => {
    el.toast.classList.remove("show");
    state.toastTimer = null;
  }, 2200);
}

function hideReviewMapFeedback() {
  if (state.reviewMapFeedbackTimer) {
    window.clearTimeout(state.reviewMapFeedbackTimer);
    state.reviewMapFeedbackTimer = null;
  }
  if (state.reviewMapFeedbackFadeTimer) {
    window.clearTimeout(state.reviewMapFeedbackFadeTimer);
    state.reviewMapFeedbackFadeTimer = null;
  }
  if (el.reviewMapFeedback) {
    el.reviewMapFeedback.classList.remove("is-visible", "is-fading");
    el.reviewMapFeedback.hidden = true;
  }
}

function captureReviewMapView() {
  if (!state.reviewMap || !state.reviewMap._loaded) {
    return null;
  }
  const center = state.reviewMap.getCenter();
  return {
    latitude: Number(center.lat),
    longitude: Number(center.lng),
    zoom: state.reviewMap.getZoom(),
  };
}

function hasActiveSessionWork() {
  return !!(
    state.dataFile
    || state.kmzFile
    || state.reviewFile
    || state.runId
    || state.lastOutputs.length
    || state.reviewQueue.length
    || state.reviewSecondaryQueue.length
    || Object.keys(state.reviewDecisions).length
    || Object.keys(state.reviewDraftPlacements).length
  );
}

function showReviewMapFeedback(message) {
  if (!el.reviewMapFeedback || !el.reviewMapFeedbackBubble) {
    showToast(message);
    return;
  }
  hideReviewMapFeedback();
  el.reviewMapFeedbackBubble.textContent = message;
  el.reviewMapFeedback.hidden = false;
  window.requestAnimationFrame(() => {
    if (!el.reviewMapFeedback) return;
    el.reviewMapFeedback.classList.add("is-visible");
    state.reviewMapFeedbackTimer = window.setTimeout(() => {
      if (!el.reviewMapFeedback) return;
      el.reviewMapFeedback.classList.add("is-fading");
      state.reviewMapFeedbackFadeTimer = window.setTimeout(() => {
        hideReviewMapFeedback();
      }, 500);
    }, 2000);
  });
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

function updateRunButton() {
  const hasData = !!state.dataFile;
  const hasKmz = !!state.kmzFile;
  const lat = el.latColumn.value.trim();
  const lon = el.lonColumn.value.trim();
  el.runRefine.disabled = !(hasData && hasKmz && lat && lon);
  if (el.stageStepInputs) {
    el.stageStepInputs.disabled = false;
  }
  updateReviewButton();
  updateRelabelButton();
  updateReadinessChecklist();
  updateStageAvailability();
  updateLabelOrderControls();
  renderStageChrome();
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
    previewMapUrl: state.previewMapUrl,
    detailsPanelOpen: state.detailsPanelOpen,
    advancedToolsOpen: state.advancedToolsOpen,
  };
  window.sessionStorage.setItem(SESSION_KEY, JSON.stringify(payload));
}

function clearUiSession() {
  window.sessionStorage.removeItem(SESSION_KEY);
  LEGACY_SESSION_KEYS.forEach((key) => window.sessionStorage.removeItem(key));
}

function readUiSession() {
  const raw = window.sessionStorage.getItem(SESSION_KEY)
    || LEGACY_SESSION_KEYS
      .map((key) => window.sessionStorage.getItem(key))
      .find(Boolean);
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
  if (el.statusBar) {
    el.statusBar.dataset.uiStage = state.uiStage;
  }
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
  el.reviewInput.value = "";
  el.latColumn.value = "";
  el.lonColumn.value = "";
  el.dataLabel.textContent = "Crash spreadsheet (.csv, .xlsx)";
  el.dataHint.textContent = "Drop file or click to browse";
  el.kmzLabel.textContent = "Boundary KMZ (.kmz)";
  el.kmzHint.textContent = "One polygon only";
  el.reviewLabel.textContent = "Reviewed coordinate workbook";
  el.reviewHint.textContent = "Upload a reviewed workbook";
  if (el.columnHint) {
    el.columnHint.hidden = false;
    el.columnHint.textContent = "Columns will populate automatically after upload.";
  }
  state.previewMapUrl = null;
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
    updateWorkflowGuidance();
    return;
  }

  if (state.uiStage === "review") {
    if (el.stageKicker) el.stageKicker.textContent = "Step 2 of 3";
    if (el.stageTitle) el.stageTitle.textContent = "Review crashes";
    if (el.stageDescription) el.stageDescription.textContent = "";
    if (el.stageNext) el.stageNext.textContent = "";
    updateWorkflowGuidance();
    return;
  }

  if (el.stageKicker) el.stageKicker.textContent = "Step 3 of 3";
  if (el.stageTitle) el.stageTitle.textContent = "Download outputs";
  if (el.stageDescription) el.stageDescription.textContent = "";
  if (el.stageNext) el.stageNext.textContent = "";
  updateWorkflowGuidance();
}

function describeCompletedAction(runKind, usedReviewWorkbook) {
  if (runKind === "relabel") return "Last action: KMZ labels regenerated";
  if (usedReviewWorkbook) return "Last action: Review decisions applied";
  return "Last action: Refinement completed";
}

function getCurrentRunFocus() {
  if (state.pollTimer || el.statusBar.dataset.state === "running") {
    return `Current run: ${el.statusTitle.textContent || "Processing"}`
      .replace(/\.$/, "")
      .concat(".");
  }
  if (state.uiStage === "inputs" && state.runId && !state.dataFile && !state.kmzFile) {
    return reviewPendingCount()
      ? "Previous run restored. Resume review or load new project files."
      : "Previous run restored. Review results or load new project files.";
  }
  if (state.uiStage === "review" && state.runId) {
    return "Current run: review likely in-project crashes and place missing coordinates.";
  }
  if (state.uiStage === "results" && state.runId) {
    return "Current run: outputs are ready for download, relabeling, or review.";
  }
  if (state.dataFile || state.kmzFile) {
    return "Current run: project inputs are loaded and ready for refinement.";
  }
  return "Current run: waiting for project files.";
}

function updateWorkflowGuidance() {
  if (el.workflowFocus) {
    el.workflowFocus.textContent = getCurrentRunFocus();
  }
  if (!el.workflowWarning) return;

  const isFreshInputsScreen = state.uiStage === "inputs" && !state.dataFile && !state.kmzFile;
  let warning = "";
  if (reviewPendingCount() && state.uiStage === "results") {
    warning = `${reviewPendingCount()} crash candidate(s) were determined to be unlikely to fall within the project limits. They remain available only if you want an extra review pass.`;
  } else if (!isFreshInputsScreen && !state.showSecondaryReview && (state.reviewSecondaryQueue || []).length) {
    warning = `${state.reviewSecondaryQueue.length} lower-likelihood crash candidate(s) are hidden until requested.`;
  } else if (state.uiStage === "inputs" && state.dataFile && state.kmzFile && !(el.latColumn.value.trim() && el.lonColumn.value.trim())) {
    warning = "Confirm latitude and longitude columns before running refinement.";
  }

  el.workflowWarning.hidden = !warning;
  el.workflowWarning.textContent = warning;
}

function syncConeTrackerToUiContext(runStatus) {
  if (runStatus === "running") {
    updateConeTracker("running");
    return;
  }
  // Restored sessions should feel calm and ready, not replay completion theatrics.
  updateConeTracker("idle", { instant: true });
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
      const data = await parseJsonSafe(response);
      if (el.columnHint) {
        el.columnHint.textContent = data.error || "Unable to detect columns.";
      }
      return;
    }

    const data = await parseJsonSafe(response);
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
  } catch (_error) {
    if (requestId !== state.headerRequestId || state.dataFile !== file) {
      return;
    }
    if (el.columnHint) {
      el.columnHint.textContent = "Unable to detect columns right now.";
    }
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
      return {
        title: "Refined crash data",
        order: 0,
        group: "Primary deliverables",
        detail: "Cleaned crash workbook filtered to the project boundary and ready for analysis.",
      };
    }
    if (/Rejected Coordinate Review/i.test(name)) {
      return {
        title: "Excluded crash review output",
        order: 4,
        group: "Review artifacts",
        detail: "Rows explicitly kept out of the project during manual review.",
      };
    }
    if (/Coordinate Recovery Review/i.test(name)) {
      return {
        title: "Coordinate recovery workbook",
        order: 3,
        group: "Review artifacts",
        detail: "Workbook of crashes that still need coordinate review outside the browser wizard.",
      };
    }
    if (/\.kmz$/i.test(name)) {
      return {
        title: "Crash KMZ",
        order: 1,
        group: "Primary deliverables",
        detail: "Map-ready KMZ with crash labels and placemarks for field review and Google Earth.",
      };
    }
    if (/Without Valid Lat-Long/i.test(name)) {
      return {
        title: "Rows missing coordinates",
        order: 5,
        group: "Review artifacts",
        detail: "Reference workbook of source rows that arrived without usable latitude and longitude values.",
      };
    }
    return {
      title: name,
      order: 10,
      group: "Additional files",
      detail: "Supporting run output.",
    };
  };

  const groupedOutputs = new Map();
  outputs
    .map((item) => ({ item, meta: describeOutput(item.name) }))
    .sort((a, b) => a.meta.order - b.meta.order || a.item.name.localeCompare(b.item.name))
    .forEach(({ item, meta }) => {
      const groupKey = meta.group;
      if (!groupedOutputs.has(groupKey)) {
        groupedOutputs.set(groupKey, []);
      }
      groupedOutputs.get(groupKey).push({ item, meta });
    });

  groupedOutputs.forEach((items, groupKey) => {
    const section = document.createElement("section");
    section.className = "output-group";
    section.innerHTML = `
      <div class="output-group-title">${escapeHtml(groupKey)}</div>
      <div class="output-group-body"></div>
    `;
    const body = section.querySelector(".output-group-body");
    items.forEach(({ item, meta }) => {
      const wrapper = document.createElement("div");
      wrapper.className = "output-item";
      wrapper.dataset.testid = `output-item-${slugify(meta.title)}`;
      wrapper.innerHTML = `
        <div>
          <div class="output-item-title">${escapeHtml(meta.title)}</div>
          <div class="output-item-detail">${escapeHtml(meta.detail)}</div>
        </div>
        <a data-testid="output-link-${slugify(item.name)}" href="/api/run/${state.runId}/download/${encodeURIComponent(item.name)}" target="_blank">${escapeHtml(item.name)}</a>
      `;
      body.appendChild(wrapper);
    });
    el.outputLinks.appendChild(section);
  });
  updateResultsSummary();
}

function setMapPreview(
  mapName,
  mapUrl,
  { rememberPreview = false, clearStoredPreview = false } = {}
) {
  state.mapReportName = mapName;
  if (clearStoredPreview) {
    state.previewMapUrl = null;
  }
  const derivedUrl = mapUrl || (mapName ? `/api/run/${state.runId}/view/${encodeURIComponent(mapName)}` : null);
  if (rememberPreview && derivedUrl) {
    state.previewMapUrl = derivedUrl;
  }
  const url = derivedUrl || (!mapName ? state.previewMapUrl || null : null);
  if (!url) {
    previewSurfaces().forEach((surface) => resetPreviewSurface(surface));
    if (el.resultsOpenMap) {
      el.resultsOpenMap.disabled = true;
      delete el.resultsOpenMap.dataset.url;
    }
    saveUiSession();
    return;
  }
  previewSurfaces().forEach((surface) => loadPreviewSurface(surface, url));
  if (el.resultsOpenMap) {
    el.resultsOpenMap.disabled = false;
    el.resultsOpenMap.dataset.url = url;
  }
  saveUiSession();
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

  try {
    const response = await fetch("/api/preview-map", { method: "POST", body: form });
    if (requestId !== state.previewRequestId) return;
    if (!response.ok) {
      const data = await parseJsonSafe(response);
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
    const data = await parseJsonSafe(response);
    if (data.latGuess && !el.latColumn.value.trim()) {
      el.latColumn.value = data.latGuess;
    }
    if (data.lonGuess && !el.lonColumn.value.trim()) {
      el.lonColumn.value = data.lonGuess;
    }
    if (data.previewUrl) {
      setMapPreview(null, data.previewUrl, { rememberPreview: true });
    }
    updateSummary();
    updateRunButton();
  } catch (_error) {
    if (requestId !== state.previewRequestId) return;
    previewSurfaces().forEach((surface) => {
      surface.frame.dataset.loaded = "false";
      surface.placeholder.textContent = "Map preview unavailable.";
      surface.placeholder.style.display = "flex";
      if (surface.button) {
        surface.button.disabled = true;
        delete surface.button.dataset.url;
      }
    });
  }
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

function formatDistanceFeet(value) {
  if (!Number.isFinite(value)) return "";
  if (value >= 5280) {
    return `${(value / 5280).toFixed(1)} mi away`;
  }
  return `${Math.round(value).toLocaleString()} ft away`;
}

function distanceFeetBetween(left, right) {
  const toRadians = (value) => (value * Math.PI) / 180;
  const earthRadiusMeters = 6371000;
  const dLat = toRadians(right.latitude - left.latitude);
  const dLon = toRadians(right.longitude - left.longitude);
  const lat1 = toRadians(left.latitude);
  const lat2 = toRadians(right.latitude);
  const a = Math.sin(dLat / 2) ** 2
    + Math.cos(lat1) * Math.cos(lat2) * Math.sin(dLon / 2) ** 2;
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  return earthRadiusMeters * c * 3.28084;
}

function getReviewReferencePoint(step) {
  const draftPlacement = getDraftPlacement(step);
  if (draftPlacement) return draftPlacement;
  const decisionPlacement = getDecisionPlacement(step);
  if (decisionPlacement) return decisionPlacement;
  if (step && step.hasSuggestion && step.suggestedLatitude != null && step.suggestedLongitude != null) {
    return {
      latitude: step.suggestedLatitude,
      longitude: step.suggestedLongitude,
    };
  }
  return null;
}

function getNearbyContextCrashes(step, limit = 3) {
  const referencePoint = getReviewReferencePoint(step);
  const contextCrashes = (state.reviewMapData && state.reviewMapData.contextCrashes) || [];
  if (!referencePoint || !contextCrashes.length) return [];

  return contextCrashes
    .map((crash) => ({
      ...crash,
      distanceFeet: Math.round(
        distanceFeetBetween(referencePoint, {
          latitude: crash.latitude,
          longitude: crash.longitude,
        })
      ),
    }))
    .sort((left, right) => left.distanceFeet - right.distanceFeet)
    .slice(0, limit);
}

function getReviewRouteContext(step) {
  if (!step) return "Route and intersection context appears here.";
  const parts = [step.title, step.detail].filter((part) => String(part || "").trim());
  return parts.length ? parts.join(" • ") : "Location context unavailable.";
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

function nextReviewStepShouldAutoCenterToSuggestion() {
  const nextStep = getCurrentReviewStep();
  return !!(
    nextStep
    && nextStep.hasSuggestion
    && nextStep.suggestedInsideBoundary !== false
    && nextStep.suggestedLatitude != null
    && nextStep.suggestedLongitude != null
  );
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
  const transportation = window.L.tileLayer(
    "https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Transportation/MapServer/tile/{z}/{y}/{x}",
    {
      maxZoom: 19,
      attribution: "Tiles (c) Esri",
      pane: "overlayPane",
    }
  );
  const labels = window.L.tileLayer(
    "https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}",
    {
      maxZoom: 19,
      attribution: "Tiles (c) Esri",
      pane: "overlayPane",
    }
  );
  const streets = window.L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19,
    attribution: "&copy; OpenStreetMap contributors",
  });
  const imageryWithRoads = window.L.layerGroup([imagery, transportation, labels]);

  imageryWithRoads.addTo(state.reviewMap);
  state.reviewMapLayers = {
    imageryWithRoads,
    imagery,
    transportation,
    labels,
    streets,
    boundary: null,
    context: window.L.layerGroup().addTo(state.reviewMap),
    suggested: window.L.layerGroup().addTo(state.reviewMap),
    selected: window.L.layerGroup().addTo(state.reviewMap),
  };
  window.L.control.layers(
    {
      "Imagery + roads": imageryWithRoads,
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
  hideReviewMapFeedback();
  el.mapMode.textContent = "Project Map";
  el.mapSubtitle.textContent = "Preview the project boundary and current outputs.";
  if (el.centerSuggestedPoint) {
    el.centerSuggestedPoint.hidden = true;
    el.centerSuggestedPoint.disabled = true;
  }
  el.wizardMap.hidden = true;
  el.mapFrame.style.display = "block";
  el.wizardMapToolbar.hidden = true;
  if (el.wizardMapContext) {
    el.wizardMapContext.textContent = "Route and intersection context appears here.";
  }
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
    el.mapSubtitle.textContent = `${current.title} ${current.detail ? `• ${current.detail}` : ""}`;
    if (el.wizardMapContext) {
      el.wizardMapContext.textContent = getReviewRouteContext(current);
    }
    if (el.wizardMapShortcuts) {
      el.wizardMapShortcuts.textContent = "Shortcuts: S suggested, C confirm pin, X exclude, N next.";
    }
    if (el.centerSuggestedPoint) {
      el.centerSuggestedPoint.hidden = !hasUsableSuggestedPoint;
      el.centerSuggestedPoint.disabled = !hasUsableSuggestedPoint;
    }
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

    if (!state.reviewMap._loaded && !state.reviewMapPreserveView) {
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

    if (state.reviewMapPendingView) {
      state.reviewMap.setView(
        [state.reviewMapPendingView.latitude, state.reviewMapPendingView.longitude],
        state.reviewMapPendingView.zoom,
        { animate: false }
      );
      state.reviewMapFocusKey = current.rowKey;
      state.reviewMapPendingView = null;
      state.reviewMapPreserveView = false;
    } else if (state.reviewMapFocusKey !== current.rowKey) {
      if (!state.reviewMapPreserveView) {
        if (activePlacement) {
          state.reviewMap.setView([activePlacement.latitude, activePlacement.longitude], 17);
        } else if (hasUsableSuggestedPoint) {
          state.reviewMap.setView([current.suggestedLatitude, current.suggestedLongitude], 17);
        } else if (boundaryBounds) {
          state.reviewMap.fitBounds(boundaryBounds, { padding: [20, 20] });
        }
      }
      state.reviewMapFocusKey = current.rowKey;
    }
    if (state.reviewMapPreserveView) {
      state.reviewMapPreserveView = false;
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
    el.clearMapSelection.textContent = "Clear Pin";
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

  if (el.reviewQueueExplainer) {
    el.reviewQueueExplainer.textContent = totalLoaded
      ? `This dataset included crashes without latitude/longitude. The application found ${visibleSteps.length || totalLoaded} crash${(visibleSteps.length || totalLoaded) === 1 ? "" : "es"} that are likely inside the project limits. Review each crash, decide whether it falls inside the project, and if it does, place it on the map so it appears correctly in the output KMZ.`
      : "This dataset included crashes without latitude/longitude. Review the likely in-project crashes, decide whether each one falls inside the project limits, and place any in-project crash on the map so it appears correctly in the output KMZ.";
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
        <section class="wizard-empty review-empty-callout" data-testid="review-empty-state">
          <div class="review-empty-kicker">Recommended next step</div>
          <div class="review-section-title">No likely crash review needed</div>
          <div class="review-section-subtitle">No crashes without lat/long data were likely inside the project boundary. Continue to results to generate the refined outputs.</div>
          <div class="review-empty-actions">
            <button class="btn primary" data-action="continue-results" data-testid="review-empty-continue-results">Continue to results</button>
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
      <section class="wizard-empty review-empty-callout" data-testid="review-empty-state">
        <div class="review-empty-kicker">Recommended next step</div>
        <div class="review-section-title">No likely crash review needed</div>
        <div class="review-section-subtitle">No crashes without lat/long data were flagged as likely inside the project boundary. Continue to results to generate the refined outputs, or open the lower-priority candidates if you want an extra pass.</div>
        <div class="review-empty-actions">
          <button class="btn primary" data-action="continue-results" data-testid="review-empty-continue-results">Continue to results</button>
          ${secondarySteps.length ? `<button class="btn secondary small" data-action="toggle-secondary" data-testid="review-toggle-secondary">Review lower-priority candidates</button>` : ""}
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
  const hasDraftPlacement = !!draftPlacement;
  const canAcceptSuggested = hasUsableSuggestedPoint && !hasDraftPlacement;
  const canPlaceOnMap = !hasDraftPlacement;
  const canExclude = !hasDraftPlacement;
  const navigationSecondaryLabel = secondarySteps.length
    ? (state.showSecondaryReview ? "Hide Lower-Likelihood Crashes" : "Load Lower-Likelihood Crashes")
    : "";
  const currentChoiceAction = choiceState.showAction && choiceState.kind !== "staged"
    ? `<button class="btn secondary small" data-action="wizard-clear-decision" data-row="${escapeHtml(current.rowKey)}" data-testid="review-clear-decision">${escapeHtml(choiceState.actionLabel)}</button>`
    : "";
  const confirmPinAction = hasDraftPlacement
    ? `<button class="btn primary small is-ready" data-action="wizard-confirm-manual" data-row="${escapeHtml(current.rowKey)}" data-testid="review-confirm-pin"${draftInside ? "" : " disabled"}>Confirm Pin</button>`
    : "";
  const clearPinAction = hasDraftPlacement
    ? `<button class="btn secondary small is-ready" data-action="wizard-clear-pin" data-row="${escapeHtml(current.rowKey)}" data-testid="review-clear-pin">Clear Pin</button>`
    : "";
  const metadataChips = metadata.length
    ? metadata.map((item) => `<span class="meta-chip">${escapeHtml(item)}</span>`).join("")
    : '<span class="meta-chip">No crash metadata</span>';
  const suggestionBadge = hasUsableSuggestedPoint
    ? `Suggested ${escapeHtml(`${formatCoordinate(current.suggestedLatitude)}, ${formatCoordinate(current.suggestedLongitude)}`)}`
    : "No suggestion";
  const nearbyCrashes = getNearbyContextCrashes(current);
  const locationSignals = [
    current.title,
    current.detail,
    hasUsableSuggestedPoint
      ? `Suggested point in project at ${formatCoordinate(current.suggestedLatitude)}, ${formatCoordinate(current.suggestedLongitude)}`
      : "No in-boundary suggested point yet",
  ].filter(Boolean);
  const nearbyContextHtml = nearbyCrashes.length
    ? `
      <details class="review-more compact review-context-panel" data-testid="review-nearby-context">
        <summary>Nearby Refined Crashes</summary>
        <div class="review-context-header">
          <div class="review-context-title">Use recent in-project crash placements as a reference.</div>
          <div class="review-context-count">${nearbyCrashes.length} nearby</div>
        </div>
        <div class="review-context-list">
          ${nearbyCrashes.map((crash) => `
            <article class="review-context-item">
              <div class="review-context-main">
                <div class="review-context-item-title">${escapeHtml(crash.title || "Refined crash")}</div>
                <div class="review-context-item-detail">${escapeHtml(crash.detail || "Refined crash inside the project boundary.")}</div>
              </div>
              <div class="review-context-meta">
                <span class="meta-chip">${escapeHtml(formatDistanceFeet(crash.distanceFeet))}</span>
                <span class="meta-chip">${escapeHtml(`${formatCoordinate(crash.latitude)}, ${formatCoordinate(crash.longitude)}`)}</span>
              </div>
            </article>
          `).join("")}
        </div>
      </details>
    `
    : "";
  const technicalDetails = reviewDetails.length || current.note
    ? `
      <details class="review-more compact">
        <summary>Details</summary>
        ${reviewDetails.length ? `<ul class="review-relevance-list">${reviewDetails.map((line) => `<li>${escapeHtml(line)}</li>`).join("")}</ul>` : ""}
        ${current.note ? `<div class="review-note">${escapeHtml(current.note)}</div>` : ""}
      </details>
    `
    : "";
  const crashNarrative = current.hasNarrative
    ? `
      <details class="review-more compact review-narrative-panel">
        <summary>Crash Narrative</summary>
        <div class="wizard-narrative-text">${escapeHtmlWithBreaks(current.narrative)}</div>
      </details>
    `
    : "";
  el.reviewList.innerHTML = `
    <section class="wizard-card ${decision ? "selected" : ""}" data-testid="review-current-card">
      <div class="wizard-progress compact">
        <div class="wizard-step-index">Crash ${state.currentReviewIndex + 1} of ${visibleSteps.length}</div>
        <div class="wizard-step-meta wizard-chip-row">${metadataChips}</div>
      </div>
      <div class="wizard-actions compact wizard-actions-primary">
        <button class="btn primary small" data-action="wizard-accept-suggested" data-row="${escapeHtml(current.rowKey)}" data-testid="review-use-suggested"${canAcceptSuggested ? "" : " disabled"}>Use suggested</button>
        <button class="btn secondary small" data-action="wizard-pick-map" data-row="${escapeHtml(current.rowKey)}" data-testid="review-place-on-map"${canPlaceOnMap ? "" : " disabled"}>${state.reviewMapPickMode ? "Picking on map" : "Place on map"}</button>
        ${confirmPinAction}
        ${clearPinAction}
        <button class="btn danger small" data-action="wizard-exclude" data-row="${escapeHtml(current.rowKey)}" data-testid="review-exclude"${canExclude ? "" : " disabled"}>Exclude</button>
        ${currentChoiceAction}
      </div>
      <section class="review-decision-panel">
        <div class="review-panel-kicker">Decision Panel</div>
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
        <div class="review-location-banner" data-testid="review-location-banner">
          ${locationSignals.map((line, index) => `
            <div class="${index === 0 ? "review-location-title" : "review-location-line"}">${escapeHtml(line)}</div>
          `).join("")}
        </div>
        <div class="wizard-chip-row review-signal-row">
          <span class="meta-chip">${escapeHtml(suggestionBadge)}</span>
          ${draftPlacement ? `<span class="meta-chip ${draftInside ? "ready" : "warn"}">Pin ${escapeHtml(`${formatCoordinate(draftPlacement.latitude)}, ${formatCoordinate(draftPlacement.longitude)}`)}</span>` : ""}
        </div>
        ${crashNarrative}
      </section>
      ${nearbyContextHtml}
      ${technicalDetails}
      <div class="wizard-nav">
        <button class="btn secondary small" data-action="wizard-prev" data-testid="review-prev"${state.currentReviewIndex > 0 ? "" : " disabled"}>Previous</button>
        <button class="btn secondary small" data-action="wizard-next" data-testid="review-next"${state.currentReviewIndex < visibleSteps.length - 1 ? "" : " disabled"}>Next</button>
        ${
          navigationSecondaryLabel
            ? `<button class="btn secondary small" data-action="toggle-secondary" data-testid="review-toggle-secondary">${escapeHtml(navigationSecondaryLabel)}</button>`
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
  try {
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
    const data = await parseJsonSafe(response);
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
  } catch (_error) {
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
  }
}

function slugify(value) {
  return String(value ?? "")
    .toLowerCase()
    .replaceAll(/[^a-z0-9]+/g, "-")
    .replaceAll(/^-+|-+$/g, "") || "item";
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
  state.reviewMapPreserveView = true;
  state.reviewDecisions[rowKey] = {
    rowKey,
    latitude: step.suggestedLatitude,
    longitude: step.suggestedLongitude,
    action: "apply",
    placementMode: "suggested",
    note: "Confirmed suggested placement in browser review workbench.",
  };
  moveToNextReviewStep(true);
  state.reviewMapPreserveView = !nextReviewStepShouldAutoCenterToSuggestion();
  showToast("Suggested crash placement saved.");
  renderReviewQueue();
}

function beginMapPlacement(rowKey) {
  const current = getCurrentReviewStep();
  const isCurrentStep = current && current.rowKey === rowKey;
  const togglingCurrentStep = current && current.rowKey === rowKey && state.reviewMapPickMode;
  focusReviewStep(rowKey);
  clearPendingExclusion();
  state.reviewMapPickMode = !togglingCurrentStep;
  if (!isCurrentStep) {
    state.reviewMapFocusKey = null;
  }
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
  state.reviewMapPreserveView = true;
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
  state.reviewMapPreserveView = !nextReviewStepShouldAutoCenterToSuggestion();
  renderReviewQueue();
  showReviewMapFeedback("Crash placed in the project.");
}

function rejectReviewCrash(rowKey) {
  if (!findReviewStep(rowKey)) {
    return;
  }
  focusReviewStep(rowKey);
  clearPendingExclusion();
  delete state.reviewDraftPlacements[rowKey];
  state.reviewMapPickMode = false;
  state.reviewMapPreserveView = true;
  state.reviewDecisions[rowKey] = {
    rowKey,
    action: "reject",
    note: "Excluded from project in browser review workbench.",
  };
  moveToNextReviewStep(true);
  state.reviewMapPreserveView = !nextReviewStepShouldAutoCenterToSuggestion();
  renderReviewQueue();
  showReviewMapFeedback("Crash excluded from the project.");
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
  state.reviewMapPendingView = captureReviewMapView();
  delete state.reviewDraftPlacements[current.rowKey];
  state.reviewMapPickMode = false;
  state.reviewMapPreserveView = true;
  renderReviewQueue();
}

async function startRun() {
  if (!state.dataFile || !state.kmzFile) return;
  clearLogs();
  clearPollingTimer();
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
  updateConeTracker("running");
  setUiBusy(true);
  el.snapshotTag.textContent = "Running";
  el.snapshotStatus.textContent = "Processing crash data.";
  el.outputLinks.textContent = "Run in progress...";

  try {
    const response = await fetch("/api/run", {
      method: "POST",
      body: buildRunFormData(),
    });
    const data = await parseJsonSafe(response);
    if (!response.ok) {
      showToast(data.error || "Unable to start refinement.");
      setStatus("error", "Run failed to start", "Check inputs and try again.");
      setProgressRunning(false);
      unlockUiAfterRun();
      return;
    }
    state.runId = data.runId;
    state.logSeq = 0;
    saveUiSession();
    await pollLogs();
    if (!state.pollTimer && el.statusBar.dataset.state === "running") {
      state.pollTimer = window.setInterval(pollLogs, 1200);
    }
  } catch (_error) {
    handleRunConnectionFailure(
      "Run failed to start",
      "Unable to reach the refinement service.",
      "Unable to start refinement."
    );
  }
}

async function startApplyReview() {
  if (!state.runId || !state.reviewFile) {
    showToast("Run refinement first, then upload a reviewed coordinate workbook.");
    return;
  }
  clearLogs();
  clearPollingTimer();
  setUiStage("results", { persist: false });
  setStatus("running", "Applying review decisions", "Re-running refinement with approved coordinates.");
  setProgressRunning(true);
  updateConeTracker("running");
  setUiBusy(true);
  el.snapshotTag.textContent = "Running";
  el.snapshotStatus.textContent = "Applying approved coordinate decisions.";
  el.outputLinks.textContent = "Run in progress...";

  try {
    const response = await fetch("/api/apply-review", {
      method: "POST",
      body: buildReviewFormData(),
    });
    const data = await parseJsonSafe(response);
    if (!response.ok) {
      showToast(data.error || "Unable to apply coordinate decisions.");
      setStatus("error", "Review apply failed", "Check the reviewed workbook and try again.");
      setProgressRunning(false);
      unlockUiAfterRun();
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
    saveUiSession();
    await pollLogs();
    if (!state.pollTimer && el.statusBar.dataset.state === "running") {
      state.pollTimer = window.setInterval(pollLogs, 1200);
    }
  } catch (_error) {
    handleRunConnectionFailure(
      "Review apply failed",
      "Unable to reach the review service.",
      "Unable to apply coordinate decisions."
    );
  }
}

async function startApplyBrowserReview() {
  if (!state.runId || Object.keys(state.reviewDecisions).length === 0) {
    showToast("Select at least one coordinate decision first.");
    return;
  }
  clearLogs();
  clearPollingTimer();
  setUiStage("results", { persist: false });
  setStatus("running", "Applying browser review", "Re-running refinement with reviewed crash placements.");
  setProgressRunning(true);
  updateConeTracker("running");
  setUiBusy(true);
  el.snapshotTag.textContent = "Running";
  el.snapshotStatus.textContent = "Applying selected crash review decisions.";
  el.outputLinks.textContent = "Run in progress...";

  try {
    const response = await fetch("/api/apply-review", {
      method: "POST",
      body: buildBrowserReviewFormData(),
    });
    const data = await parseJsonSafe(response);
    if (!response.ok) {
      showToast(data.error || "Unable to apply browser review decisions.");
      setStatus("error", "Browser review failed", "Check the selected decisions and try again.");
      setProgressRunning(false);
      unlockUiAfterRun();
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
    saveUiSession();
    await pollLogs();
    if (!state.pollTimer && el.statusBar.dataset.state === "running") {
      state.pollTimer = window.setInterval(pollLogs, 1200);
    }
  } catch (_error) {
    handleRunConnectionFailure(
      "Browser review failed",
      "Unable to reach the review service.",
      "Unable to apply browser review decisions."
    );
  }
}

async function startRelabel() {
  if (!state.runId) {
    showToast("Run refinement first.");
    return;
  }
  clearLogs();
  clearPollingTimer();
  setUiStage("results", { persist: false });
  setStatus("running", "Regenerating labels", "Updating the refined spreadsheet and KMZ numbering.");
  setProgressRunning(true);
  updateConeTracker("running");
  setUiBusy(true);
  el.snapshotTag.textContent = "Running";
  el.snapshotStatus.textContent = "Regenerating KMZ labels.";
  el.outputLinks.textContent = "Relabel in progress...";

  try {
    const response = await fetch(`/api/run/${state.runId}/relabel`, {
      method: "POST",
      body: buildRelabelFormData(),
    });
    const data = await parseJsonSafe(response);
    if (!response.ok) {
      showToast(data.error || "Unable to regenerate labels.");
      setStatus("error", "Label regeneration failed", "Check the requested direction and try again.");
      setProgressRunning(false);
      unlockUiAfterRun();
      return;
    }
    await pollLogs();
    if (!state.pollTimer && el.statusBar.dataset.state === "running") {
      state.pollTimer = window.setInterval(pollLogs, 1200);
    }
  } catch (_error) {
    handleRunConnectionFailure(
      "Label regeneration failed",
      "Unable to reach the relabel service.",
      "Unable to regenerate labels."
    );
  }
}

/* ── Cone Guy Tracker Logic ──────────────────────────────────────────── */

const CONE_MILESTONES = [
  { id: "load", label: "Load", progress: 18 },
  { id: "normalize", label: "Normalize", progress: 40 },
  { id: "filter", label: "Filter", progress: 65 },
  { id: "output", label: "Output", progress: 90 },
];

function getConeRuntimeSignals() {
  const texts = state.logLines.slice(-50);
  const combined = texts.join(" ").toLowerCase();
  return {
    hasLoaded: combined.includes("loaded") && combined.includes("crash rows"),
    hasBoundary: combined.includes("loaded kmz boundary"),
    hasRecovery: combined.includes("coordinate recovery"),
    hasFilter: combined.includes("boundary filter complete"),
    hasLabels: combined.includes("kmz labels ordered"),
    hasRefined: combined.includes("refined output saved"),
    hasKmz: combined.includes("kmz report generated"),
    hasReviewApply: combined.includes("review decisions"),
    hasRelabel: combined.includes("relabel") || combined.includes("labels regenerated"),
    hasValidated: combined.includes("output invariants validated"),
    combined,
  };
}

function getConeMilestone(phase) {
  if (phase === "success") return "output";
  if (phase === "error") return "normalize";
  if (phase === "idle") return "load";
  const sig = getConeRuntimeSignals();
  if (sig.hasRefined || sig.hasKmz || sig.hasValidated) return "output";
  if (sig.hasFilter || sig.hasLabels) return "filter";
  if (sig.hasRecovery || (sig.hasLoaded && sig.hasBoundary)) return "normalize";
  return "load";
}

function getConeProgress(phase, milestoneId) {
  if (phase === "success") return 90;
  if (phase === "error") return 40;
  const sig = getConeRuntimeSignals();
  if (milestoneId === "output") {
    if (sig.hasValidated) return 90;
    if (sig.hasKmz) return 86;
    if (sig.hasRefined) return 78;
    return 72;
  }
  if (milestoneId === "filter") {
    if (sig.hasLabels) return 62;
    if (sig.hasFilter) return 55;
    return 48;
  }
  if (milestoneId === "normalize") {
    if (sig.hasRecovery) return 35;
    if (sig.hasLoaded && sig.hasBoundary) return 28;
    if (sig.hasLoaded || sig.hasBoundary) return 22;
    return 18;
  }
  return 10;
}

function getConeNote(phase, milestoneId) {
  const sig = getConeRuntimeSignals();
  if (phase === "success") {
    if (sig.hasRelabel) return "Fresh KMZ labels are ready.";
    if (sig.hasReviewApply) return "Approved placements folded into outputs.";
    return "Lane clear. Outputs are ready.";
  }
  if (phase === "error") return "Work zone blocked. Check the run log.";
  if (phase === "idle") return "Waiting for a new assignment.";
  if (milestoneId === "load") return sig.hasBoundary ? "Boundary loaded. Reading crash rows." : "Loading crash data and project boundary.";
  if (milestoneId === "normalize") return "Checking headers and recovering likely coordinates.";
  if (milestoneId === "filter") return "Comparing crash patterns against the project boundary.";
  if (milestoneId === "output") return "Writing the workbook, KMZ, and review artifacts.";
  return "Processing.";
}

function getConeCalcValues(milestoneId, phase) {
  const sig = getConeRuntimeSignals();
  if (phase === "success") {
    if (sig.hasRelabel) return ["KMZ", "ORDER", "DONE"];
    return ["DONE", "CLEAR", "READY"];
  }
  if (phase === "error") return ["ERR", "LOG", "FIX"];
  if (phase === "idle") return ["IDLE"];
  if (milestoneId === "load") return ["CSV", "KMZ", "HDR", "SCAN"];
  if (milestoneId === "normalize") return ["LAT", "LON", "GPS?", "MATCH"];
  if (milestoneId === "filter") return ["IN?", "KMZ", "ROUTE", "KEEP", "CUT"];
  if (sig.hasRelabel) return ["KMZ", "ORDER", "WEST", "DONE"];
  return ["XLSX", "KMZ", "ZIP", "DONE"];
}

function setConeMotion(root, nextProgress, phase, milestoneId, { instant = false } = {}) {
  if (instant) {
    if (state.coneGuy.driveTimer) {
      window.clearTimeout(state.coneGuy.driveTimer);
      state.coneGuy.driveTimer = null;
    }
    if (state.coneGuy.settleTimer) {
      window.clearTimeout(state.coneGuy.settleTimer);
      state.coneGuy.settleTimer = null;
    }
    root.classList.add("is-restoring");
    root.classList.remove("is-driving", "is-settling");
    state.coneGuy.progress = nextProgress;
    window.requestAnimationFrame(() => {
      window.requestAnimationFrame(() => {
        root.classList.remove("is-restoring");
      });
    });
    return;
  }
  if (state.coneGuy.progress === nextProgress) return;
  const wasBeforeFinish = state.coneGuy.progress < 90;
  state.coneGuy.progress = nextProgress;
  root.classList.add("is-driving");
  root.classList.remove("is-settling");
  if (state.coneGuy.driveTimer) window.clearTimeout(state.coneGuy.driveTimer);
  state.coneGuy.driveTimer = window.setTimeout(() => {
    root.classList.remove("is-driving");
    state.coneGuy.driveTimer = null;
    if ((phase === "success" || milestoneId === "output") && wasBeforeFinish) {
      root.classList.add("is-settling");
      if (state.coneGuy.settleTimer) window.clearTimeout(state.coneGuy.settleTimer);
      state.coneGuy.settleTimer = window.setTimeout(() => {
        root.classList.remove("is-settling");
        state.coneGuy.settleTimer = null;
      }, 1800);
    }
  }, 3000);
}

function updateConeTracker(phase, { instant = false, restored = false } = {}) {
  if (!el.coneTracker) return;
  if (!phase) {
    phase = state.pollTimer ? "running" : "idle";
  }
  const milestoneId = getConeMilestone(phase);
  const milestone = CONE_MILESTONES.find((m) => m.id === milestoneId) || CONE_MILESTONES[0];
  const progress = getConeProgress(phase, milestoneId);
  const root = el.coneTracker;

  root.classList.remove(
    "is-idle", "is-running", "is-success", "is-error", "is-restored-complete",
    "phase-load", "phase-normalize", "phase-filter", "phase-output"
  );
  root.classList.add(`is-${phase}`);
  if (restored && phase === "success") {
    root.classList.add("is-restored-complete");
  }
  root.classList.add(`phase-${milestoneId}`);
  root.style.setProperty("--cone-progress", `${progress}%`);
  setConeMotion(root, progress, phase, milestoneId, { instant });

  if (el.coneTrackerState) {
    el.coneTrackerState.textContent =
      phase === "success" ? "Lane clear" :
      phase === "error" ? "Needs review" :
      phase === "running" ? milestone.label :
      "Awaiting run";
  }
  if (el.coneTrackerNote) {
    el.coneTrackerNote.textContent = getConeNote(phase, milestoneId);
  }
  if (el.coneTrackerGuidance) {
    el.coneTrackerGuidance.textContent =
      phase === "success" ? "Your outputs are ready in the Results step." :
      phase === "error" ? "Check the log and review items that still need attention." :
      phase === "running" ? "Cone Guy is keeping an eye on the workflow while the run is in progress." :
      "Add your crash spreadsheet and boundary file to get started.";
  }

  const prevMilestone = state.coneGuy.milestone;
  el.coneTrackerNodes.forEach((node) => {
    const nodeMilestone = node.dataset.coneNode;
    const nodeProgress = CONE_MILESTONES.find((m) => m.id === nodeMilestone)?.progress ?? 0;
    node.classList.remove("is-active", "is-done");
    if (nodeMilestone === milestoneId) {
      node.classList.add("is-active");
      if (prevMilestone !== milestoneId) {
        node.classList.remove("is-flash");
        void node.offsetWidth;
        node.classList.add("is-flash");
        setTimeout(() => node.classList.remove("is-flash"), 400);
      }
    } else if (nodeProgress < progress || phase === "success") {
      node.classList.add("is-done");
    }
  });
  state.coneGuy.milestone = milestoneId;
  syncConeCalcTimer(milestoneId, phase);
}

function setConeCalcScreen(text) {
  if (!el.coneTrackerCalcScreen) return;
  el.coneTrackerCalcScreen.textContent = text;
  const sx = text.length <= 1 ? 1 : Math.min(1, 1.6 / text.length);
  el.coneTrackerCalcScreen.style.transform = `scaleX(${sx})`;
  el.coneTrackerCalcScreen.style.transformOrigin = "right center";
}

function syncConeCalcTimer(milestoneId, phase) {
  const values = getConeCalcValues(milestoneId, phase);
  const signature = `${phase}:${milestoneId}:${values.join("|")}`;
  if (state.coneGuy.calcSignature === signature) {
    return;
  }
  state.coneGuy.calcSignature = signature;
  if (state.coneGuy.calcCycleTimer) {
    clearInterval(state.coneGuy.calcCycleTimer);
    state.coneGuy.calcCycleTimer = null;
  }
  setConeCalcScreen(values[0] || "Σ");
  if (phase !== "running" || values.length <= 1) {
    return;
  }
  let idx = 0;
  const intervalMs = milestoneId === "filter" ? 820 : (milestoneId === "output" ? 980 : 1150);
  state.coneGuy.calcCycleTimer = setInterval(() => {
    idx = (idx + 1) % values.length;
    setConeCalcScreen(values[idx]);
  }, intervalMs);
}

async function pollLogs() {
  if (!state.runId) return;
  try {
    const response = await fetch(`/api/run/${state.runId}/log?since=${state.logSeq}`);
    if (!response.ok) {
      if (response.status === 404) {
        handleRunConnectionFailure(
          "Run unavailable",
          "The saved run could not be found.",
          "Run session is no longer available.",
          { clearSession: true }
        );
      }
      return;
    }
    const data = await parseJsonSafe(response);
    state.logSeq = data.lastSeq || state.logSeq;
    appendLog(data.entries || []);
    if (data.status === "running" && data.message) {
      el.statusDetail.textContent = data.message;
      el.snapshotStatus.textContent = data.message;
    }
    if (data.status === "running") {
      updateConeTracker("running");
    }
    if (data.status && data.status !== "running") {
      clearPollingTimer();
      await finalizeRun(data.status);
    }
  } catch (_error) {
    handleRunConnectionFailure(
      "Run connection lost",
      "Lost connection while streaming run activity.",
      "Lost connection to the running job."
    );
  }
}

async function finalizeRun(status) {
  try {
    const response = await fetch(`/api/run/${state.runId}`);
    if (!response.ok) {
      handleRunConnectionFailure(
        "Run failed",
        "Unable to retrieve final run status.",
        "Unable to load the finished run."
      );
      state.reviewQueue = [];
      renderReviewQueue();
      return;
    }
    const data = await parseJsonSafe(response);
    state.runInputs = data.inputs || state.runInputs;
    state.lastRunSummary = data.summary || null;
    state.lastOutputs = data.outputs || [];
    setLabelOrderSelection((state.runInputs && state.runInputs.labelOrder) || "auto", { scope: "results" });
    const runKind = (data.inputs && data.inputs.runKind) || "refine";
    const usedReviewWorkbook = !!(
      data.inputs && (data.inputs.coordinateReviewFile || data.inputs.browserReviewDecisionCount)
    );
    if (status === "success") {
      const successTitle = runKind === "relabel"
        ? "Labels regenerated"
        : (usedReviewWorkbook ? "Review decisions applied" : "Refinement complete");
      const successSnapshot = runKind === "relabel"
        ? "Refined output and KMZ labels were updated."
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
      const errorTitle = runKind === "relabel"
        ? "Label regeneration failed"
        : (usedReviewWorkbook ? "Review apply failed" : "Refinement failed");
      const errorSnapshot = runKind === "relabel"
        ? "Relabeling encountered errors."
        : (usedReviewWorkbook
          ? "Approved coordinate rerun encountered errors."
          : "Refinement encountered errors.");
      const errorToast = runKind === "relabel"
        ? "Regenerating labels failed."
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
    } else if (state.previewMapUrl) {
      setMapPreview(null, state.previewMapUrl);
    } else {
      setMapPreview(null, null, { clearStoredPreview: true });
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
      el.snapshotLastRun.textContent = `${describeCompletedAction(runKind, usedReviewWorkbook)} at ${new Date(finishedAt).toLocaleString()}`;
    }
    setProgressRunning(false);
    updateConeTracker(status === "success" ? "success" : "error");
    unlockUiAfterRun();
    updateResultsSummary();
    updateLabelOrderControls();
    renderStageChrome();
    saveUiSession();
  } catch (_error) {
    handleRunConnectionFailure(
      "Run failed",
      "Unable to load the finished run state.",
      "Unable to load the finished run."
    );
    state.reviewQueue = [];
    renderReviewQueue();
  }
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
          body { margin: 0; background: #0f172a; color: #e2e8f0; font-family: "Segoe UI", Tahoma, Geneva, Verdana, sans-serif; }
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

    const data = await parseJsonSafe(response);
    state.runId = saved.runId;
    state.runInputs = data.inputs || saved.runInputs || null;
    state.lastRunSummary = data.summary || saved.lastRunSummary || null;
    state.lastOutputs = data.outputs || saved.lastOutputs || [];
    state.previewMapUrl = saved.previewMapUrl || null;
    setLabelOrderSelection((state.runInputs && state.runInputs.labelOrder) || "auto", { scope: "results" });
    renderOutputs(state.lastOutputs);
    renderMetrics(state.lastRunSummary || {});
    if (data.summary && data.summary.mapReport) {
      setMapPreview(data.summary.mapReport);
    } else if (state.previewMapUrl) {
      setMapPreview(null, state.previewMapUrl);
    }
    if (data.finishedAt) {
      const restoreRunKind = (data.inputs && data.inputs.runKind) || "refine";
      const restoredReviewWorkbook = !!(
        data.inputs && (data.inputs.coordinateReviewFile || data.inputs.browserReviewDecisionCount)
      );
      el.snapshotLastRun.textContent = `${describeCompletedAction(restoreRunKind, restoredReviewWorkbook)} at ${new Date(data.finishedAt).toLocaleString()}`;
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
      const runningTitle = runKind === "relabel"
        ? "Regenerating labels"
        : (runKind === "review" ? "Applying review decisions" : "Refinement running");
      setStatus("running", runningTitle, data.message || "Run in progress.");
      el.snapshotTag.textContent = "Running";
      el.snapshotStatus.textContent = data.message || "Run in progress.";
      setProgressRunning(true);
      state.logSeq = 0;
      await pollLogs();
      if (!state.pollTimer) {
        state.pollTimer = window.setInterval(pollLogs, 1200);
      }
    } else {
      const runKind = (data.inputs && data.inputs.runKind) || "refine";
      const usedReviewWorkbook = !!(
        data.inputs && (data.inputs.coordinateReviewFile || data.inputs.browserReviewDecisionCount)
      );
      if (data.status === "success") {
        setStatus(
          "success",
          runKind === "relabel"
            ? "Labels regenerated"
            : (usedReviewWorkbook ? "Review decisions applied" : "Refinement complete"),
          data.message || "Outputs ready."
        );
        el.snapshotTag.textContent = "Complete";
        el.snapshotStatus.textContent = runKind === "relabel"
          ? "Refined output and KMZ labels were updated."
          : (usedReviewWorkbook
            ? "Refinement reran with approved coordinates."
            : "Refinement completed successfully.");
      } else if (data.status) {
        setStatus(
          "error",
          runKind === "relabel"
            ? "Label regeneration failed"
            : (usedReviewWorkbook ? "Review apply failed" : "Refinement failed"),
          data.message || "Review the run log."
        );
        el.snapshotTag.textContent = "Failed";
        el.snapshotStatus.textContent = runKind === "relabel"
          ? "Relabeling encountered errors."
          : (usedReviewWorkbook
            ? "Approved coordinate rerun encountered errors."
            : "Refinement encountered errors.");
      }
      syncConeTrackerToUiContext(data.status || "");
      setProgressRunning(false);
      unlockUiAfterRun();
    }
    setAdvancedToolsOpen(!!saved.advancedToolsOpen);
    setTechnicalDetailsOpen(!!saved.detailsPanelOpen);
    updateStageAvailability();
    updateRunButton();
    updateLabelOrderControls();
    if (data.status === "running") {
      setUiBusy(true);
    }
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
  const openFilePicker = () => {
    if (!input || input.disabled) return;
    if (typeof input.showPicker === "function") {
      input.showPicker();
      return;
    }
    input.click();
  };

  zone.setAttribute("role", "button");
  zone.setAttribute("tabindex", input.disabled ? "-1" : "0");

  zone.addEventListener("click", (event) => {
    if (event.target === input) return;
    openFilePicker();
  });
  zone.addEventListener("keydown", (event) => {
    if (event.key !== "Enter" && event.key !== " ") return;
    event.preventDefault();
    openFilePicker();
  });
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
  if (el.centerSuggestedPoint) {
    el.centerSuggestedPoint.addEventListener("click", () => {
      const current = getCurrentReviewStep();
      if (!current || !state.reviewMap || !(current.hasSuggestion && current.suggestedLatitude != null && current.suggestedLongitude != null)) {
        return;
      }
      state.reviewMap.setView([current.suggestedLatitude, current.suggestedLongitude], 17);
      showToast("Centered on the suggested placement.");
    });
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
    if (target.dataset.action === "wizard-clear-pin") {
      clearCurrentMapPlacement();
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
    if (hasActiveSessionWork()) {
      const confirmed = window.confirm(
        "Start over and clear the current files, review work, and results?"
      );
      if (!confirmed) {
        return;
      }
    }
    clearPollingTimer();
    if (state.previewTimer) {
      window.clearTimeout(state.previewTimer);
      state.previewTimer = null;
    }
    state.previewRequestId = 0;
    state.runId = null;
    state.logSeq = 0;
    clearLogs();
    setUiBusy(false);
    state.dataFile = null;
    state.kmzFile = null;
    state.reviewFile = null;
    state.runInputs = null;
    state.lastRunSummary = null;
    state.lastOutputs = [];
    state.previewMapUrl = null;
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
    el.reviewLabel.textContent = "Reviewed coordinate workbook";
    el.reviewHint.textContent = "Upload a reviewed workbook";
    updateColumnOptions([]);
    setStatus("idle", "Ready to run", "Add crash data, boundary, and columns.");
    setProgressRunning(false);
    updateConeTracker("idle");
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
    setMapPreview(null, null, { clearStoredPreview: true });
    renderReviewQueue();
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
    if ((key === "s" || key === "u") && current.hasSuggestion && current.suggestedInsideBoundary !== false) {
      event.preventDefault();
      confirmSuggestedPlacement(current.rowKey);
      return;
    }
    if (key === "p") {
      event.preventDefault();
      beginMapPlacement(current.rowKey);
      return;
    }
    if ((key === "c" || key === "enter")) {
      const draftPlacement = getDraftPlacement(current);
      if (draftPlacement && pointInProjectBoundary(draftPlacement.latitude, draftPlacement.longitude)) {
        event.preventDefault();
        confirmManualPlacement(current.rowKey);
        return;
      }
    }
    if (key === "n") {
      event.preventDefault();
      moveToNextReviewStep();
      state.reviewMapPickMode = false;
      state.reviewMapFocusKey = null;
      renderReviewQueue();
      return;
    }
    if (key === "x") {
      event.preventDefault();
      toggleCrashExclusion(current.rowKey);
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
  updateReviewButton();
  setReviewWorkbenchTab("map");
  setLabelOrderSelection("auto");
  setUiStage("inputs", { persist: false });
  setAdvancedToolsOpen(false);
  setTechnicalDetailsOpen(false);
  restoreUiSession();
}

init();
