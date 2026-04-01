import { chromium } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const repoRoot = path.resolve(__dirname, "..");
const outputDir = path.join(repoRoot, "outputs", "qc_browser_smoke");
const appUrl = process.env.CDR_QC_URL || "http://127.0.0.1:8090";
const crashDataPath = process.env.CDR_QC_DATA_PATH || path.join(repoRoot, "tests", "refiner_inputs", "2101166_Crash-Data.xlsx");
const kmzPath = process.env.CDR_QC_KMZ_PATH || path.join(repoRoot, "tests", "refiner_inputs", "2101166_Relevance Boundary.kmz");
const expectedAutoLabelOrder = (process.env.CDR_QC_EXPECTED_AUTO_LABEL_ORDER || "south_to_north").toLowerCase();
const datasetLabel = process.env.CDR_QC_DATASET_LABEL || path.basename(crashDataPath);

fs.mkdirSync(outputDir, { recursive: true });

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function waitForServer(url, timeoutMs = 30000) {
  const deadline = Date.now() + timeoutMs;
  let lastError = null;
  while (Date.now() < deadline) {
    try {
      const response = await fetch(url, { redirect: "manual" });
      if (response.ok || response.status === 304) {
        return;
      }
      lastError = new Error(`Unexpected status ${response.status}`);
    } catch (error) {
      lastError = error;
    }
    await sleep(500);
  }
  throw new Error(`Server did not become ready at ${url}: ${lastError}`);
}

function assert(condition, message) {
  if (!condition) {
    throw new Error(message);
  }
}

async function waitForStage(page, stageId, timeout = 180000) {
  await page.locator(`${stageId}.is-active`).waitFor({ timeout });
}

function logStep(message) {
  console.log(`[qc:web] ${message}`);
}

function labelOrderText(order) {
  return order.replaceAll("_", " ");
}

async function waitForSuccessSnapshot(page, timeout = 180000) {
  await page.waitForFunction(() => {
    const tag = document.querySelector("#snapshot-tag");
    const statusBar = document.querySelector("#status-bar");
    return tag && /complete/i.test(tag.textContent || "") && statusBar?.dataset.state === "success";
  }, undefined, { timeout });
}

async function run() {
  await waitForServer(appUrl, 30000);
  logStep(`Server ready at ${appUrl}`);

  const browser = await chromium.launch();
  try {
    const page = await browser.newPage({ viewport: { width: 1600, height: 1200 } });
    const serverErrors = [];
    page.on("response", (response) => {
      if (response.status() >= 500) {
        serverErrors.push(`${response.status()} ${response.url()}`);
      }
    });

    await page.goto(appUrl, { waitUntil: "domcontentloaded" });
    logStep("Opened app landing page.");
    await page.locator("#data-input").setInputFiles(crashDataPath);
    await page.locator("#kmz-input").setInputFiles(kmzPath);
    await page.waitForFunction(() => {
      const lat = document.querySelector("#lat-column");
      const lon = document.querySelector("#lon-column");
      const runButton = document.querySelector("#run-refine");
      return lat && lon && lat.value && lon.value && runButton && !runButton.disabled;
    }, undefined, { timeout: 30000 });
    logStep("Sample files loaded and coordinate columns inferred.");

    await page.locator("#run-refine").click();
    await waitForStage(page, "#stage-view-review", 180000);
    await page.locator('[data-action="wizard-exclude"]').first().waitFor({ timeout: 60000 });
    logStep("Refinement completed and review stage loaded.");

    const suggestedPlacementText = ((await page.locator(".wizard-suggestion-body").first().textContent()) || "").trim();
    if (suggestedPlacementText.startsWith("Suggested point:")) {
      assert(
        !/0\.000000,\s*0\.000000/.test(suggestedPlacementText),
        `Review wizard surfaced an origin suggested placement for ${datasetLabel}: ${suggestedPlacementText}`,
      );
      assert(
        !/\(outside KMZ\)/i.test(suggestedPlacementText),
        `Review wizard surfaced an outside-KMZ suggested placement for ${datasetLabel}: ${suggestedPlacementText}`,
      );
      logStep("First suggested placement passed browser sanity checks.");
    }
    await page.screenshot({ path: path.join(outputDir, "review-stage.png"), fullPage: true });

    await page.reload({ waitUntil: "domcontentloaded" });
    await waitForStage(page, "#stage-view-review", 60000);
    await page.locator('[data-action="wizard-exclude"]').first().waitFor({ timeout: 60000 });
    logStep("Review stage restored correctly after hard refresh.");

    const excludeButton = page.locator('[data-action="wizard-exclude"]').first();
    await excludeButton.scrollIntoViewIfNeeded();
    await excludeButton.click();
    await page.getByRole("button", { name: "Confirm Exclusion" }).click();
    await page.waitForFunction(() => {
      const button = document.querySelector("#apply-browser-review");
      return button && !button.disabled;
    }, undefined, { timeout: 30000 });
    logStep("One crash excluded and review apply became available.");

    await page.locator("#apply-browser-review").click();
    await waitForStage(page, "#stage-view-results", 180000);
    await waitForSuccessSnapshot(page, 180000);
    logStep("Reviewed decisions applied and Results stage loaded.");

    const summaryText = await page.locator("#results-summary-line").textContent();
    assert(
      /\b[1-9]\d* row\(s\) were excluded from the project by manual review\./.test(summaryText || ""),
      `Manual exclusion count did not update in Results summary: ${summaryText}`,
    );

    const initialLabelStatus = (await page.locator("#results-label-order-status").textContent()) || "";
    assert(
      initialLabelStatus.toLowerCase().includes(labelOrderText(expectedAutoLabelOrder)),
      `Automatic label ordering did not resolve ${labelOrderText(expectedAutoLabelOrder)} for ${datasetLabel}: ${initialLabelStatus}`,
    );
    logStep(`Automatic label ordering resolved to ${labelOrderText(expectedAutoLabelOrder)} for ${datasetLabel}.`);

    await page.screenshot({ path: path.join(outputDir, "results-stage-before-relabel.png"), fullPage: true });

    await page.reload({ waitUntil: "domcontentloaded" });
    await waitForStage(page, "#stage-view-results", 60000);
    await page.locator("#results-relabel").waitFor({ timeout: 60000 });
    logStep("Results stage restored correctly after hard refresh.");

    await page.locator("#results-label-order").selectOption("west_to_east");
    await Promise.all([
      page.waitForResponse((response) => response.url().includes("/relabel") && response.status() === 200, { timeout: 120000 }),
      page.locator("#results-relabel").click(),
    ]);
    await page.reload({ waitUntil: "domcontentloaded" });
    await waitForStage(page, "#stage-view-results", 120000);
    await waitForSuccessSnapshot(page, 180000);
    await page.waitForFunction(() => {
      const status = document.querySelector("#results-label-order-status");
      return status && /west to east/i.test(status.textContent || "");
    }, undefined, { timeout: 120000 });

    const relabeledStatus = (await page.locator("#results-label-order-status").textContent()) || "";
    assert(
      /west to east/i.test(relabeledStatus),
      `Relabeling did not update the Results status text: ${relabeledStatus}`,
    );
    logStep("Relabel flow completed successfully.");

    await page.screenshot({ path: path.join(outputDir, "results-stage-after-relabel.png"), fullPage: true });
    assert(serverErrors.length === 0, `Unexpected server 500 responses detected:\n${serverErrors.join("\n")}`);
    console.log("Browser smoke QC passed.");
  } finally {
    await browser.close();
  }
}

run().catch((error) => {
  console.error(error.stack || String(error));
  process.exitCode = 1;
});
