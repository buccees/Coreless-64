#!/usr/bin/env node
"use strict";

const assert = require("node:assert/strict");
const http = require("node:http");
const fs = require("node:fs");
const path = require("node:path");
const { chromium } = require("playwright");

const htmlPath = path.join(__dirname, "..", "index.html");
const html = fs.readFileSync(htmlPath);
const fixture = {
  model_id: "BROWSER-TEST-MODEL",
  revision: "r1",
  frame_id: "frame-browser-test",
  features: [],
  objects: [
    {
      object_id: "TRACK-STABLE",
      normalized_position: [0.2, 0.3, 0],
      inferred_level: "1",
      uncertainty_m: 0.5,
      calibration_status: "verified",
      calibration_ids: ["CAL-1"],
      lineage_declared: true,
      observation_count: 4,
      sensor_ids: ["LIDAR-A"],
      modalities: ["lidar"],
      independence_groups: ["range-a"]
    },
    {
      object_id: "TRACK-UNKNOWN",
      normalized_position: [0.4, 0.3, 0],
      inferred_level: "1",
      calibration_status: "verified",
      lineage_declared: true,
      observation_count: 2,
      sensor_ids: ["CAM-A"],
      modalities: ["optical"]
    },
    {
      object_id: "TRACK-REVIEW",
      normalized_position: [0.6, 0.3, 0],
      inferred_level: "1",
      uncertainty_m: 1.4,
      calibration_status: "pending",
      lineage_declared: false,
      observation_count: 3,
      sensor_ids: ["LIDAR-B"],
      modalities: ["lidar"],
      conflict: true,
      conflict_reasons: ["browser fixture conflict"]
    }
  ]
};

(async () => {
  const server = http.createServer((req, res) => {
    if (req.url === "/" || req.url === "/index.html") {
      res.writeHead(200, { "content-type": "text/html; charset=utf-8" });
      res.end(html);
      return;
    }
    res.writeHead(404); res.end("not found");
  });
  await new Promise(resolve => server.listen(0, "127.0.0.1", resolve));
  const address = server.address();
  const browser = await chromium.launch({ headless: true });
  const errors = [];
  try {
    const context = await browser.newContext({ acceptDownloads: true, viewport: { width: 1440, height: 1000 } });
    const page = await context.newPage();
    page.on("pageerror", error => errors.push(error.message));
    await page.goto("http://127.0.0.1:" + address.port + "/", { waitUntil: "load" });

    await page.locator('.nav-button[data-view="spatial"]').click();
    await page.locator("#spatial-panel .spatial-stage").waitFor({ state: "visible" });
    assert.equal(await page.locator("#spatial-audit-panel").isVisible(), true);
    assert.match(await page.locator(".spatial-legend").innerText(), /UNKNOWN UNCERTAINTY \/ AMBER DASHED/);
    assert.match(await page.locator(".spatial-legend").innerText(), /BLUE DASHED OUTLINE/);

    await page.locator("#spatial-json").setInputFiles({
      name: "browser-fixture.json",
      mimeType: "application/json",
      buffer: Buffer.from(JSON.stringify(fixture))
    });
    await page.waitForFunction(() => document.querySelector("#spatial-status").textContent.includes("IMPORTED BROWSER-TEST-MODEL"));
    assert.equal(await page.locator('#imported-object-layer [data-track-id="TRACK-STABLE"]').count(), 1);
    assert.equal(await page.locator('#imported-object-layer [data-track-id="TRACK-UNKNOWN"].uncertainty-unknown').count(), 1);
    assert.equal(await page.locator('#imported-object-layer [data-track-id="TRACK-REVIEW"].metadata-review').count(), 1);
    assert.equal(await page.locator('#imported-object-layer [data-track-id="TRACK-REVIEW"].conflict').count(), 1);

    await page.locator('.spatial-review-filter[data-review-filter="missing"]').click();
    assert.equal(await page.locator('.spatial-review-filter[data-review-filter="missing"]').getAttribute("aria-pressed"), "true");
    assert.equal(await page.locator('#imported-object-layer [data-track-id="TRACK-STABLE"]').evaluate(el => el.style.opacity), "0.12");
    assert.equal(await page.locator('#imported-object-layer [data-track-id="TRACK-REVIEW"]').evaluate(el => el.style.opacity), "1");
    await page.locator('.spatial-review-filter[data-review-filter="review"]').click();
    assert.equal(await page.locator('#imported-object-layer [data-track-id="TRACK-UNKNOWN"]').evaluate(el => el.style.opacity), "1");

    await page.locator('#imported-object-layer [data-track-id="TRACK-REVIEW"]').click();
    await page.locator(".spatial-review-decision").waitFor({ state: "visible" });
    assert.match(await page.locator("#spatial-track-detail").innerText(), /REVIEW REQUIRED/);
    await page.locator(".spatial-review-controls select").selectOption("NEEDS FOLLOW-UP");
    await page.locator(".spatial-review-controls input").fill("Browser test: verify calibration and conflict evidence.");
    await page.locator(".spatial-review-controls button").click();
    await page.waitForFunction(() => document.querySelector("#spatial-audit-list").innerText.includes("TRACK REVIEW DECISION"));
    assert.match(await page.locator(".spatial-review-current").innerText(), /NEEDS FOLLOW-UP/);
    assert.match(await page.locator("#spatial-audit-list").innerText(), /verify calibration and conflict evidence/);

    const downloadPromise = page.waitForEvent("download");
    await page.locator("#spatial-audit-export").click();
    const download = await downloadPromise;
    const downloadPath = path.join(require("node:os").tmpdir(), download.suggestedFilename());
    await download.saveAs(downloadPath);
    const exported = JSON.parse(fs.readFileSync(downloadPath, "utf8"));
    fs.unlinkSync(downloadPath);
    assert.equal(exported.format, "VIGIL-spatial-audit");
    assert.ok(exported.events.some(event => event.action === "TRACK REVIEW DECISION"));

    // Reload checks browser persistence for both the audit history and review decision.
    await page.reload({ waitUntil: "load" });
    await page.locator('.nav-button[data-view="spatial"]').click();
    assert.match(await page.locator("#spatial-audit-list").innerText(), /TRACK REVIEW DECISION/);
    await page.locator("#spatial-json").setInputFiles({
      name: "browser-fixture.json",
      mimeType: "application/json",
      buffer: Buffer.from(JSON.stringify(fixture))
    });
    await page.waitForFunction(() => document.querySelector("#spatial-status").textContent.includes("IMPORTED BROWSER-TEST-MODEL"));
    await page.locator('#imported-object-layer [data-track-id="TRACK-REVIEW"]').click();
    assert.match(await page.locator(".spatial-review-current").innerText(), /NEEDS FOLLOW-UP/);
    assert.match(await page.locator(".spatial-review-controls input").inputValue(), /verify calibration and conflict evidence/);

    await page.locator("#spatial-audit-clear").click();
    assert.match(await page.locator("#spatial-audit-status").innerText(), /^0 EVENTS/);
    assert.deepEqual(errors, [], "browser page must not throw uncaught JavaScript errors");

    // Check the mobile viewport doesn't create horizontal page overflow.
    await page.setViewportSize({ width: 390, height: 844 });
    const dimensions = await page.evaluate(() => ({
      viewport: document.documentElement.clientWidth,
      page: document.documentElement.scrollWidth
    }));
    assert.ok(dimensions.page <= dimensions.viewport + 2,
      "mobile page should not overflow horizontally: " + JSON.stringify(dimensions));

    console.log("VIGIL browser integration: import, marker states, review filters, decision persistence, audit export/clear, runtime errors, and mobile layout passed.");
    await context.close();
  } finally {
    await browser.close();
    await new Promise(resolve => server.close(resolve));
  }
})().catch(error => {
  console.error(error);
  process.exitCode = 1;
});
