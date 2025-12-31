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
  columnOptions: document.getElementById("column-options"),
  columnHint: document.getElementById("column-hint"),
  generatePdf: document.getElementById("generate-pdf"),
  progressBar: document.getElementById("progress-bar"),
  statusBar: document.getElementById("status-bar"),
  statusTitle: document.getElementById("status-title"),
  statusDetail: document.getElementById("status-detail"),
  runRefine: document.getElementById("run-refine"),
  clearSession: document.getElementById("clear-session"),
  summaryData: document.getElementById("summary-data"),
  summaryKmz: document.getElementById("summary-kmz"),
  summaryColumns: document.getElementById("summary-columns"),
  summaryPdf: document.getElementById("summary-pdf"),
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

function updateRunButton() {
  const hasData = !!state.dataFile;
  const hasKmz = !!state.kmzFile;
  const lat = el.latColumn.value.trim();
  const lon = el.lonColumn.value.trim();
  el.runRefine.disabled = !(hasData && hasKmz && lat && lon);
}

function updateSummary() {
  el.summaryData.textContent = state.dataFile ? state.dataFile.name : "No file selected.";
  el.summaryKmz.textContent = state.kmzFile ? state.kmzFile.name : "No boundary selected.";
  const lat = el.latColumn.value.trim();
  const lon = el.lonColumn.value.trim();
  el.summaryColumns.textContent = lat && lon ? `${lat} / ${lon}` : "Latitude / Longitude not set.";
  if (!el.generatePdf.checked) {
    el.summaryPdf.textContent = "PDF report disabled.";
  } else if (state.pdfDataFile) {
    el.summaryPdf.textContent = state.pdfDataFile.name;
  } else {
    el.summaryPdf.textContent = "Refined output (default).";
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

function setMapPreview(mapName) {
  state.mapReportName = mapName;
  if (!mapName) {
    el.mapFrame.removeAttribute("src");
    el.mapPlaceholder.style.display = "flex";
    el.openMap.disabled = true;
    return;
  }
  const url = `/api/run/${state.runId}/view/${encodeURIComponent(mapName)}`;
  el.mapFrame.src = url;
  el.mapPlaceholder.style.display = "none";
  el.openMap.disabled = false;
  el.openMap.dataset.url = url;
}

function buildRunFormData() {
  const form = new FormData();
  form.append("data_file", state.dataFile);
  form.append("boundary_file", state.kmzFile);
  form.append("lat_column", el.latColumn.value.trim());
  form.append("lon_column", el.lonColumn.value.trim());
  form.append("generate_pdf", el.generatePdf.checked ? "true" : "false");
  if (state.pdfDataFile) {
    form.append("pdf_data_file", state.pdfDataFile);
  }
  return form;
}

async function startRun() {
  if (!state.dataFile || !state.kmzFile) return;
  clearLogs();
  setStatus("running", "Refinement running", "Crash data pipeline is processing.");
  setProgressRunning(true);
  el.runRefine.disabled = true;
  el.snapshotTag.textContent = "Running";
  el.snapshotStatus.textContent = "Processing crash data.";
  el.outputLinks.textContent = "Run in progress...";
  setMapPreview(null);

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

function handleGeneratePdfToggle() {
  const enabled = el.generatePdf.checked;
  el.pdfInput.disabled = !enabled;
  el.pdfDrop.style.opacity = enabled ? "1" : "0.5";
  el.pdfHint.textContent = enabled
    ? "Leave blank to use refined data."
    : "PDF generation is disabled.";
  updateSummary();
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
  });
  el.lonColumn.addEventListener("input", () => {
    updateSummary();
    updateRunButton();
  });
  el.generatePdf.addEventListener("change", handleGeneratePdfToggle);
  el.runRefine.addEventListener("click", startRun);
  el.clearSession.addEventListener("click", () => {
    if (state.pollTimer) {
      window.clearInterval(state.pollTimer);
      state.pollTimer = null;
    }
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
    el.dataLabel.textContent = "Drop crash data (CSV or Excel)";
    el.dataHint.textContent = "Drag a file here or click to browse.";
    el.kmzLabel.textContent = "Drop KMZ polygon boundary";
    el.kmzHint.textContent = "Must contain exactly one polygon.";
    el.pdfLabel.textContent = "Drop alternate PDF data file";
    el.pdfHint.textContent = el.generatePdf.checked
      ? "Leave blank to use refined data."
      : "PDF generation is disabled.";
    updateColumnOptions([]);
    setStatus("idle", "Ready to run", "Add crash data and a KMZ polygon to begin refinement.");
    setProgressRunning(false);
    el.snapshotTag.textContent = "Idle";
    el.snapshotStatus.textContent = "Waiting for inputs.";
    el.snapshotLastRun.textContent = "No runs yet.";
    el.outputLinks.textContent = "No outputs yet.";
    el.metrics.innerHTML = "";
    setMapPreview(null);
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
  handleGeneratePdfToggle();
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
  });
  window.addEventListener("dragover", (event) => event.preventDefault());
  window.addEventListener("drop", (event) => event.preventDefault());
  updateSummary();
  updateRunButton();
}

init();
