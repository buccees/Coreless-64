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
    assert.equal(await page.locator("#site-settings-backdrop").isVisible(), false, "closed settings overlay must not cover Spatial Intelligence controls");
    assert.equal(await page.locator("#spatial-json").isEnabled(), true, "scene import file input must be enabled");
    await page.locator("#spatial-json").scrollIntoViewIfNeeded();
    const importHitTest = await page.locator("#spatial-json").evaluate(el => { const r = el.getBoundingClientRect(); const x = r.left + r.width / 2, y = r.top + r.height / 2; const hit = document.elementFromPoint(x, y); const backdrop = document.querySelector("#site-settings-backdrop"); return { hit: hit === el || el.contains(hit), target: hit ? { tag: hit.tagName, id: hit.id, className: typeof hit.className === "string" ? hit.className : "" } : null, inputRect: { x: r.x, y: r.y, width: r.width, height: r.height }, backdrop: { hidden: backdrop.hidden, display: getComputedStyle(backdrop).display, visibility: getComputedStyle(backdrop).visibility, pointerEvents: getComputedStyle(backdrop).pointerEvents } }; });
    console.log("SCENE IMPORT POINTER DIAGNOSTIC " + JSON.stringify(importHitTest));
    assert.equal(importHitTest.hit, true, "scene import control must receive pointer events rather than being covered by an overlay");
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
    assert.match(await page.locator("#spatial-track-detail").innerText(), /TRACK REVIEW HISTORY \/\/ CURRENT SCENE/);
    assert.match(await page.locator(".spatial-track-history").innerText(), /TRACK REVIEW DECISION/);
    assert.match(await page.locator(".spatial-track-history").innerText(), /verify calibration and conflict evidence/);
    assert.match(await page.locator("#spatial-audit-list").innerText(), /verify calibration and conflict evidence/);

    const downloadPromise = page.waitForEvent("download");
    await page.locator("#spatial-audit-export").click();
    const download = await downloadPromise;
    const downloadPath = path.join(require("node:os").tmpdir(), download.suggestedFilename());
    await download.saveAs(downloadPath);
    const exported = JSON.parse(fs.readFileSync(downloadPath, "utf8"));
    fs.unlinkSync(downloadPath);
    assert.equal(exported.format, "VIGIL-spatial-audit");
    assert.equal(exported.version, 2);
    assert.equal(exported.event_count, exported.events.length);
    assert.match(exported.exported_at, /^\d{4}-\d{2}-\d{2}T/);
    assert.ok(exported.session_id);
    assert.equal(exported.active_scene.model_id, "BROWSER-TEST-MODEL");
    const exportedDecisionEvent = exported.events.find(event => event.action === "TRACK REVIEW DECISION");
    assert.ok(exportedDecisionEvent);
    assert.equal(exportedDecisionEvent.scene.model_id, "BROWSER-TEST-MODEL");
    assert.equal(exportedDecisionEvent.scene.revision, "r1");
    assert.equal(exportedDecisionEvent.scene.frame_id, "frame-browser-test");
    assert.equal(exportedDecisionEvent.track_id, "TRACK-REVIEW");
    assert.ok(exported.review_decisions.some(decision =>
      decision.model_id === "BROWSER-TEST-MODEL" &&
      decision.revision === "r1" &&
      decision.frame_id === "frame-browser-test" &&
      decision.track_id === "TRACK-REVIEW" &&
      decision.decision === "NEEDS FOLLOW-UP"
    ));

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

    // Storage failure and malformed persisted JSON must degrade to an explicit session-only mode.
    for (const storageMode of ["unavailable", "corrupt"]) {
      const storageContext = await browser.newContext({ acceptDownloads: true, viewport: { width: 1280, height: 900 } });
      const storageErrors = [];
      await storageContext.addInitScript((mode) => {
        const auditKey = "coreless64-vigil-spatial-audit-v1";
        const decisionKey = "coreless64-vigil-track-review-decisions-v1";
        const originalGet = Storage.prototype.getItem;
        const originalSet = Storage.prototype.setItem;
        const originalRemove = Storage.prototype.removeItem;
        Storage.prototype.getItem = function(key) {
          if (mode === "unavailable" && (key === auditKey || key === decisionKey)) throw new Error("simulated storage unavailable");
          if (mode === "corrupt" && key === auditKey) return "{malformed-json";
          if (mode === "corrupt" && key === decisionKey) return "[]";
          return originalGet.call(this, key);
        };
        if (mode === "unavailable") {
          Storage.prototype.setItem = function(key, value) {
            if (key === auditKey || key === decisionKey) throw new Error("simulated storage unavailable");
            return originalSet.call(this, key, value);
          };
          Storage.prototype.removeItem = function(key) {
            if (key === auditKey || key === decisionKey) throw new Error("simulated storage unavailable");
            return originalRemove.call(this, key);
          };
        }
      }, storageMode);
      const storagePage = await storageContext.newPage();
      storagePage.on("pageerror", error => storageErrors.push(error.message));
      await storagePage.goto("http://127.0.0.1:" + address.port + "/", { waitUntil: "load" });
      await storagePage.locator('.nav-button[data-view="spatial"]').click();
      assert.match(await storagePage.locator("#spatial-audit-status").innerText(), /SESSION ONLY/);
      await storagePage.locator("#spatial-json").setInputFiles({
        name: "browser-fixture.json",
        mimeType: "application/json",
        buffer: Buffer.from(JSON.stringify(fixture))
      });
      await storagePage.waitForFunction(() => document.querySelector("#spatial-status").textContent.includes("IMPORTED BROWSER-TEST-MODEL"));
      await storagePage.locator('#imported-object-layer [data-track-id="TRACK-REVIEW"]').click();
      await storagePage.locator(".spatial-review-controls select").selectOption("ESCALATED");
      await storagePage.locator(".spatial-review-controls input").fill("Storage resilience test decision.");
      await storagePage.locator(".spatial-review-controls button").click();
      await storagePage.waitForFunction(() => document.querySelector("#spatial-audit-list").innerText.includes("TRACK REVIEW DECISION"));
      assert.match(await storagePage.locator(".spatial-review-current").innerText(), /ESCALATED/);
      assert.match(await storagePage.locator("#spatial-audit-status").innerText(), /SESSION ONLY/);
      const storageDownloadPromise = storagePage.waitForEvent("download");
      await storagePage.locator("#spatial-audit-export").click();
      const storageDownload = await storageDownloadPromise;
      const storageExportPath = path.join(require("node:os").tmpdir(), storageDownload.suggestedFilename());
      await storageDownload.saveAs(storageExportPath);
      const storageExport = JSON.parse(fs.readFileSync(storageExportPath, "utf8"));
      fs.unlinkSync(storageExportPath);
      assert.equal(storageExport.active_scene.model_id, "BROWSER-TEST-MODEL");
      assert.ok(storageExport.review_decisions.some(decision => decision.track_id === "TRACK-REVIEW" && decision.decision === "ESCALATED"));
      assert.deepEqual(storageErrors, [], storageMode + " storage mode must not throw uncaught page errors");
      await storageContext.close();
    }

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
