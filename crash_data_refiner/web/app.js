const state = {
  dataFile: null,
  kmzFile: null,
  pdfDataFile: null,
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
  latColumn: document.getElementById("lat-column"),
  lonColumn: document.getElementById("lon-column"),
  labelOrder: document.getElementById("label-order"),
  columnOptions: document.getElementById("column-options"),
  columnHint: document.getElementById("column-hint"),
  generateReport: document.getElementById("generate-report"),
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
  openMap: document.getElementById("open-map"),
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
}

function updateReportButton() {
  const hasSource = !!state.pdfDataFile || !!state.runId || !!state.dataFile;
  el.generateReport.disabled = !hasSource;
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

async function startRun() {
  if (!state.dataFile || !state.kmzFile) return;
  clearLogs();
  setStatus("running", "Refinement running", "Crash data pipeline is processing.");
  setProgressRunning(true);
  setReportProgressRunning(false);
  el.runRefine.disabled = true;
  el.generateReport.disabled = true;
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

async function pollLogs() {
  if (!state.runId) return;
  const response = await fetch(`/api/run/${state.runId}/log?since=${state.logSeq}`);
  if (!response.ok) return;
  const data = await response.json();
  state.logSeq = data.lastSeq || state.logSeq;
  appendLog(data.entries || []);
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
    updateRunButton();
    return;
  }
  const data = await response.json();
  if (status === "success") {
    setStatus("success", "Refinement complete", data.message || "Outputs ready.");
    el.snapshotTag.textContent = "Complete";
    el.snapshotStatus.textContent = "Refinement completed successfully.";
  } else {
    setStatus("error", "Refinement failed", data.message || "Review the run log.");
    el.snapshotTag.textContent = "Failed";
    el.snapshotStatus.textContent = "Refinement encountered errors.";
    showToast(data.error || "Refinement failed.");
  }

  renderOutputs(data.outputs || []);
  renderMetrics(data.summary || {});
  setMapPreview(data.summary ? data.summary.mapReport : null);

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
    el.dataInput.value = "";
    el.kmzInput.value = "";
    el.pdfInput.value = "";
    el.latColumn.value = "";
    el.lonColumn.value = "";
    el.labelOrder.selectedIndex = 0;
    el.dataLabel.textContent = "Drop crash data (CSV or Excel)";
    el.dataHint.textContent = "Drag a file here or click to browse.";
    el.kmzLabel.textContent = "Drop KMZ polygon boundary";
    el.kmzHint.textContent = "Must contain exactly one polygon.";
    el.pdfLabel.textContent = "Drop alternate PDF data file";
    el.pdfHint.textContent = "Leave blank to use refined output when available.";
    updateColumnOptions([]);
    setStatus("idle", "Ready to run", "Add crash data and a KMZ polygon to begin refinement.");
    setProgressRunning(false);
    el.snapshotTag.textContent = "Idle";
    el.snapshotStatus.textContent = "Waiting for inputs.";
    el.snapshotLastRun.textContent = "No runs yet.";
    el.outputLinks.textContent = "No outputs yet.";
    el.metrics.innerHTML = "";
    el.mapPlaceholder.textContent = "Map report preview appears after crash data and boundary files are loaded.";
    setMapPreview(null);
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
  window.addEventListener("dragover", (event) => event.preventDefault());
  window.addEventListener("drop", (event) => event.preventDefault());
  updateSummary();
  updateRunButton();
  setReportProgressRunning(false);
}

init();
