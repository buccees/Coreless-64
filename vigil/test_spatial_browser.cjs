#!/usr/bin/env node
"use strict";

const assert = require("node:assert/strict");
const http = require("node:http");
const fs = require("node:fs");
const path = require("node:path");
const { chromium } = require("playwright");

const htmlPath = path.join(__dirname, "..", "index.html");
const html = fs.readFileSync(htmlPath);
const fixture = require("./fixtures/vigil-test-scene.json");

(async () => {
  const server = http.createServer((req, res) => {
    if (req.url === "/" || req.url === "/index.html") {
      res.writeHead(200, { "content-type": "text/html; charset=utf-8" });
      res.end(html);
      return;
    }
    if (req.url === "/vigil/simulation-catalog.js") {
      res.writeHead(200, { "content-type": "text/javascript; charset=utf-8" });
      res.end(fs.readFileSync(path.join(__dirname, "simulation-catalog.js")));
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
    await page.locator('.nav-button[data-view="simulation"]').click();
    await page.locator("#sim-campaign-panel").waitFor({ state: "visible" });
    assert.equal(await page.locator("#sim-level-select option").count(), 5, "campaign must expose five data-driven levels");
    assert.match(await page.locator("#sim-fow-status").innerText(), /GROUND TRUTH: NOT EXPOSED/);
    const catalogUnits = await page.evaluate(() => window.vigilSimulationCatalog.getUnits());
    assert.ok(catalogUnits.some(unit => unit.domain === "air" && unit.id === "scout-drone"), "catalog must include a drone profile");
    const gagSub = catalogUnits.find(unit => unit.id === "prank-submersible");
    assert.ok(gagSub && gagSub.is_bonus === true && gagSub.inventory === 1 && gagSub.max_deployed === 1 && /phallic/i.test(gagSub.silhouette) && /JOKE BONUS UNIT ONLY/.test(gagSub.notes), "Level 5 must include a clearly labelled fictional phallic gag submarine with finite capacity");
    assert.ok(catalogUnits.every(unit => unit.inventory > 0 && unit.max_deployed > 0 && unit.max_deployed <= unit.inventory && unit.endurance_minutes > 0), "unit definitions must have finite, valid capacity and endurance");
    const globalHawk = catalogUnits.find(unit => unit.id === "long-endurance-uav");
    const reaper = catalogUnits.find(unit => unit.id === "mq-9a-reaper");
    assert.ok(globalHawk && globalHawk.specification_source && globalHawk.model_asset_url.endsWith(".glb") && globalHawk.model_asset_page_url && globalHawk.dimensions_m.wingspan === 39.8, "Global Hawk must include sourced specifications, dimensions, and a direct GLB model asset");
    assert.ok(reaper && reaper.specification_source && reaper.endurance_minutes === 1620 && reaper.model_asset_format === "sketchfab-embed" && reaper.model_asset_page_url && reaper.model_asset_attribution && /Creative Commons Attribution/.test(reaper.model_asset_license), "MQ-9A profile must expose an attributed, license-labelled remote 3D preview");
    await page.locator("#sim-level-select").selectOption("level-3");
    assert.ok(await page.locator("#sim-unit-roster").innerText().then(text => text.includes("model source") && text.includes("Specs: source") && text.includes("REMOTE LOAD")), "roster must expose source, geometry provenance, and remote-asset status");
    const globalHawkViewer = page.locator("#sim-unit-roster model-viewer");
    assert.equal(await globalHawkViewer.count(), 1, "Global Hawk roster entry must render an interactive 3D model viewer");
    assert.match(await globalHawkViewer.getAttribute("src"), /Global%20Hawk\.glb$/, "viewer must load the sourced NASA GLB asset");
    const reaperViewer = page.locator("#sim-unit-roster iframe[title*=\"MQ-9A Reaper\"]");
    assert.equal(await reaperViewer.count(), 1, "MQ-9A roster entry must render its interactive third-party 3D preview");
    assert.match(await reaperViewer.getAttribute("src"), /sketchfab\.com\/models\/eff549610fee4f20904f7b388a3a0830\/embed$/, "MQ-9A viewer must use the attributed Sketchfab model");
    assert.ok((await page.locator("#sim-unit-roster").innerText()).includes("REMOTE EMBED"), "third-party model must be clearly marked as remote and not bundled");
    const droneDeployments = await page.evaluate(() => {
      const first = window.vigilSimulationCatalog.deploy("scout-drone");
      let result = first;
      for (let i = 0; i < 12; i++) result = window.vigilSimulationCatalog.deploy("scout-drone");
      return { first, result, state: window.vigilSimulationCatalog.getState() };
    });
    assert.equal(droneDeployments.first.ok, true);
    assert.equal(droneDeployments.state.deployed["scout-drone"], 6, "drone deployment must respect the configured max-deployed limit");
    assert.equal(droneDeployments.result.ok, false, "deploying beyond capacity must be rejected");
    const enduranceCheck = await page.evaluate(() => {
      const api = window.vigilSimulationCatalog;
      const before = api.getState().clockMinutes;
      const tick = api.advanceTime(15);
      const after = api.getState();
      return { tick, before, after };
    });
    assert.equal(enduranceCheck.tick.ok, true, "mission clock should advance by a valid step");
    assert.equal(enduranceCheck.after.clockMinutes, enduranceCheck.before + 15);
    assert.equal(enduranceCheck.after.sorties.filter(s => s.unitId === "scout-drone" && s.status === "DEPLOYED").every(s => s.remainingMinutes === 75), true, "deployed drones must burn 15 minutes of endurance");
    const recoveryCheck = await page.evaluate(() => {
      const api = window.vigilSimulationCatalog;
      const recovery = api.recover("scout-drone");
      const state = api.getState();
      return { recovery, state };
    });
    assert.equal(recoveryCheck.recovery.ok, true, "active sortie should be recoverable");
    assert.equal(recoveryCheck.state.recovering["scout-drone"], 1, "recovered unit must enter turnaround instead of becoming instantly available");
    assert.equal(recoveryCheck.state.ready["scout-drone"], 6, "recovering unit must remain unavailable from fleet inventory");
    const invalidTick = await page.evaluate(() => window.vigilSimulationCatalog.advanceTime(-5));
    assert.equal(invalidTick.ok, false, "negative time steps must be rejected");
    await page.locator("#sim-level-select").selectOption("level-4");
    assert.match(await page.locator("#sim-level-brief").innerText(), /DEGRADED SENSORS/);
    assert.equal(await page.locator("#sim-unit-roster [data-unit-id]").count(), 6, "scenario level should load its configured roster including the newly added MQ-9A profile");


    await page.locator('.nav-button[data-view="spatial"]').click();
    await page.locator("#spatial-panel .spatial-stage").waitFor({ state: "visible" });
    assert.equal(await page.locator("#site-settings-backdrop").isVisible(), false, "closed settings overlay must not cover Spatial Intelligence controls");
    assert.equal(await page.locator("#spatial-import-open").isVisible(), true, "scene import action must be visible near the top of Spatial Intelligence");
    assert.equal(await page.locator("#spatial-import-open").isEnabled(), true, "scene import action must be enabled");
    assert.equal(await page.locator("#spatial-audit-panel").isVisible(), true);
    assert.match(await page.locator(".spatial-legend").innerText(), /UNKNOWN UNCERTAINTY \/ AMBER DASHED/);
    assert.match(await page.locator(".spatial-legend").innerText(), /BLUE DASHED OUTLINE/);

    const sceneChooserPromise = page.waitForEvent("filechooser");
    await page.locator("#spatial-import-open").click();
    const sceneChooser = await sceneChooserPromise;
    await sceneChooser.setFiles({
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

    // Simulation Bay: grid mechanics, repeat-shot collision guard, and sensor-only publication.
    await page.locator('.nav-button[data-view="simulation"]').click();
    await page.locator("#simulation-panel").waitFor({ state: "visible" });
    assert.equal(await page.locator("#sim-board .sim-cell").count(), 100, "simulation grid must contain exactly 100 cells");
    assert.equal(await page.locator("#sim-afloat").innerText(), "5", "new exercise must initialize all five vessels");
    const firstCell = page.locator("#sim-board .sim-cell").first();
    await firstCell.click();
    assert.equal(await page.locator("#sim-shots").innerText(), "1", "one cell action must resolve exactly one shot");
    assert.equal(await firstCell.isDisabled(), true, "resolved cells must not be targetable twice");
    await page.locator("#sim-publish").click();
    await page.waitForFunction(() => document.querySelector("#spatial-status").textContent.includes("IMPORTED VIGIL-SIMULATION-BAY"));
    assert.ok(await page.locator('#imported-object-layer [data-track-id^="SIM-"]').count() > 0, "simulation must publish sensor-estimated tracks to Spatial Intelligence");
    assert.match(await page.locator("#sim-telemetry").innerText(), /WORLD-STATE ACCESS: DENIED TO VIGIL/);
    assert.match(await page.locator("#spatial-audit-list").innerText(), /SIMULATION OBSERVATIONS PUBLISHED/);
    assert.ok(await page.locator("#sim-recon-contacts .sim-recon-contact").count() > 0, "recon register must expose observed contacts");
    const contactId = await page.locator("#sim-recon-contacts .sim-recon-contact").first().getAttribute("data-contact-id");
    assert.match(contactId, /^SIM-EXERCISE-\d+-CONTACT-\d{3}$/, "contact identifiers must be opaque and must not disclose return classes");
    await page.locator("#sim-recon-contacts .sim-recon-contact").first().click();
    assert.match(await page.locator("#sim-recon-detail").innerText(), /CONTACT EVIDENCE[\s\S]*POSITION UNCERTAINTY/);
    await page.locator("#sim-recon-evaluate").click();
    assert.match(await page.locator("#sim-recon-results").innerText(), /MEAN GENUINE-CONTACT POSITION ERROR/);
    assert.match(await page.locator("#sim-recon-results").innerText(), /FALSE RETURNS: \d+ \/ \d+ \([\d.]+% of observed returns\)/);
    assert.match(await page.locator("#sim-recon-results").innerText(), /MISSED GENUINE CONTACTS: 0 \/ 5 \(0\.0% missed\)/);
    assert.match(await page.locator("#sim-recon-results").innerText(), /DETECTION RATE: 100\.0%/);
    assert.equal(await page.locator("#sim-recon-contacts .sim-recon-contact").count(), 8, "default clutter setting should add three false returns to five genuine contacts");
    const detectionRateControl = page.locator("#sim-detection-rate");
    await detectionRateControl.selectOption("0");
    await page.locator("#sim-recon-sweep").click();
    assert.equal(await page.locator("#sim-recon-contacts .sim-recon-contact").count(), 3, "sensor outage should suppress genuine returns while preserving configured clutter");
    await page.locator("#sim-recon-evaluate").click();
    assert.match(await page.locator("#sim-recon-results").innerText(), /MISSED GENUINE CONTACTS: 5 \/ 5 \(100\.0% missed\)/);
    assert.match(await page.locator("#sim-recon-results").innerText(), /DETECTION RATE: 0\.0%/);
    await detectionRateControl.selectOption("100");
    const clutterCountControl = page.locator("#sim-clutter-count");
    await clutterCountControl.selectOption("0");
    await page.locator("#sim-recon-sweep").click();
    assert.equal(await page.locator("#sim-recon-contacts .sim-recon-contact").count(), 5, "baseline mode should emit only genuine contacts");
    await page.locator("#sim-recon-evaluate").click();
    assert.match(await page.locator("#sim-recon-results").innerText(), /FALSE RETURNS: 0 \/ 5 \(0\.0% of observed returns\)/);
    assert.match(await page.locator("#sim-recon-results").innerText(), /GROUND TRUTH: USED ONLY INSIDE THIS EVALUATOR/);
    await page.locator("#sim-recon-sweep").click();
    await page.waitForFunction(() => document.querySelector("#spatial-status").textContent.includes("IMPORTED VIGIL-SIMULATION-BAY"));
    const repeatedTrackLabel = await page.locator("#sim-recon-contacts .sim-recon-contact").first().innerText();
    assert.ok(Number(repeatedTrackLabel.split("OBS ")[1].split(" //")[0]) >= 2, "repeat sweeps must preserve contact history");
    assert.equal(await page.locator("#sim-recon-investigate").isEnabled(), true, "selecting a contact must enable focused investigation");
    await page.locator("#sim-recon-investigate").click();
    await page.waitForFunction(() => document.querySelector("#sim-turn-status").textContent.includes("FOCUSED FOLLOW-UP"));
    const focusedDetail = await page.locator("#sim-recon-detail").innerText();
    assert.match(focusedDetail, /FOCUSED FOLLOW-UP RECEIVED[\s\S]*OBSERVATIONS IN TRACK: \d+/);
    assert.ok(Number(focusedDetail.match(/OBSERVATIONS IN TRACK: (\d+)/)[1]) >= 3, "focused follow-up must append to existing track history");
    assert.match(await page.locator("#sim-recon-results").innerText(), /VIGIL RECEIVED ONLY THE SELECTED CONTACT OBSERVATION/);
    const directSensorResponse = await page.evaluate(id => window.vigilSensorBridge.requestObservation({
      action: "focused_observation", contact_id: id, sensor_mode: "optical", request_id: "BROWSER-DIRECT-REQ"
    }), contactId);
    assert.equal(directSensorResponse.ok, true, "VIGIL sensor bridge must fulfill a valid focused observation request");
    assert.equal(directSensorResponse.request_id, "BROWSER-DIRECT-REQ");
    assert.equal(directSensorResponse.requested_by, "VIGIL");
    assert.equal(directSensorResponse.contact_id, contactId);
    assert.equal(directSensorResponse.sensor_mode, "optical", "VIGIL must be able to request a specific simulated sensor modality");
    assert.equal(directSensorResponse.observation.modalities[0], "optical");
    assert.equal(directSensorResponse.world_state_withheld, true);
    assert.equal(Object.hasOwn(directSensorResponse, "ground_truth"), false, "sensor responses must not expose evaluator truth");
    assert.equal(Object.hasOwn(directSensorResponse.observation, "vesselIndex"), false, "individual observations must not expose internal truth labels");
    assert.equal(directSensorResponse.observation.observation_count >= 4, true, "VIGIL-requested observation must append to track history");
    const eventSensorResponse = await page.evaluate(id => {
      let response = null;
      const receive = event => { response = event.detail; };
      window.addEventListener("vigil:sensor-response", receive);
      window.dispatchEvent(new CustomEvent("vigil:sensor-request", { detail: {
        action: "focused_observation", contact_id: id, sensor_mode: "radar", request_id: "BROWSER-EVENT-REQ"
      }}));
      window.removeEventListener("vigil:sensor-response", receive);
      return response;
    }, contactId);
    assert.equal(eventSensorResponse.ok, true, "VIGIL event-based sensor requests must return a response");
    assert.equal(eventSensorResponse.request_id, "BROWSER-EVENT-REQ");
    assert.equal(eventSensorResponse.observation.modalities[0], "radar");
    const priorAutoObservationCount = Number(await page.locator("#sim-observations").innerText());
    await page.locator("#sim-recon-autopilot").click();
    await page.waitForFunction(() => document.querySelector("#sim-vigil-decision").textContent.includes("WORLD STATE: WITHHELD"));
    const autoRecon = await page.evaluate(() => ({
      history: window.vigilReconController.getHistory(),
      next: window.vigilReconController.chooseNextAction(),
      output: document.querySelector("#sim-vigil-decision").textContent
    }));
    assert.equal(autoRecon.history.length, 1, "VIGIL policy must record an autonomous recon decision");
    assert.equal(autoRecon.history[0].contact_id.length > 0, true);
    assert.ok(["radar", "sonar", "optical"].includes(autoRecon.history[0].sensor_mode));
    assert.match(autoRecon.history[0].rationale, /greatest reported position uncertainty/i);
    assert.equal(autoRecon.history[0].world_state_withheld, true, "decision history must confirm evaluator truth remained withheld");
    assert.match(autoRecon.output, /VIGIL DECISION[\s\S]*RATIONALE:[\s\S]*RESULT:/);
    assert.ok(Number(await page.locator("#sim-observations").innerText()) >= priorAutoObservationCount, "autonomous recon step must preserve the observation metric");
    assert.equal(Object.hasOwn(autoRecon.history[0], "ground_truth"), false, "decision history must not expose evaluator truth");
    await page.locator("#sim-recon-autopilot").click();
    await page.waitForFunction(() => document.querySelector("#sim-vigil-decision").textContent.includes("STEP 02"));
    const decisionTrail = await page.evaluate(() => ({
      history: window.vigilReconController.getHistory(),
      output: document.querySelector("#sim-vigil-decision").textContent
    }));
    assert.equal(decisionTrail.history.length, 2, "the visible decision trail must preserve consecutive VIGIL steps");
    assert.match(decisionTrail.output, /STEP 01[\s\S]*STEP 02[\s\S]*WORLD STATE: WITHHELD/);
    await page.locator("#sim-view-fleet").click();
    assert.equal(await page.locator("#sim-view-fleet").getAttribute("aria-pressed"), "true", "own-fleet inspection must expose its active state");
    assert.ok(await page.locator("#sim-board .sim-cell.ship").count() >= 17, "own-fleet view must render all 17 vessel cells");
    assert.equal(await page.locator("#sim-board .sim-cell:not(:disabled)").count(), 0, "own-fleet inspection must not allow firing at friendly cells");
    await page.locator("#sim-view-fleet").click();
    assert.equal(await page.locator("#sim-board .sim-cell.ship").count(), 0, "returning to firing grid must conceal friendly vessel positions");
    const resetBefore = await page.locator("#sim-shots").innerText();
    await page.locator("#sim-new-game").click();
    assert.equal(await page.locator("#sim-shots").innerText(), "0", "new exercise must reset engagement count");
    assert.equal(await page.locator("#sim-board .sim-cell").count(), 100, "reset must rebuild a complete grid");
    await page.locator("#sim-manual-setup").click();
    assert.match(await page.locator("#sim-turn-status").innerText(), /PLACE CARRIER/);
    await page.locator("#sim-board .sim-cell").nth(0).hover();
    assert.equal(await page.locator("#sim-board .placement-preview").count(), 5, "placement preview must show the current ship footprint");
    await page.locator("#sim-board .sim-cell").nth(0).click();
    assert.match(await page.locator("#sim-turn-status").innerText(), /PLACE BATTLESHIP/);
    await page.locator("#sim-rotate").click();
    await page.locator("#sim-board .sim-cell").nth(99).click();
    assert.match(await page.locator("#sim-turn-status").innerText(), /INVALID PLACEMENT/);
    assert.equal(await page.locator("#sim-board .sim-cell.ship").count(), 5, "invalid out-of-bounds placement must not alter the fleet");
    await page.locator("#sim-rotate").click();
    await page.locator("#sim-board .sim-cell").nth(5).click();
    await page.locator("#sim-board .sim-cell").nth(20).click();
    await page.locator("#sim-board .sim-cell").nth(24).click();
    await page.locator("#sim-board .sim-cell").nth(28).click();
    assert.match(await page.locator("#sim-turn-status").innerText(), /FLEETS READY/);
    assert.equal(await page.locator("#sim-board .sim-cell.ship").count(), 0, "completed setup returns to the concealed firing grid");
    await page.locator("#sim-view-fleet").click();
    assert.equal(await page.locator("#sim-board .sim-cell.ship").count(), 17, "manual setup must place all 17 vessel cells");
    await page.locator("#sim-new-game").click();
    assert.deepEqual(errors, [], "simulation interactions must not throw uncaught JavaScript errors");
    assert.notEqual(await page.locator("#sim-shots").innerText(), resetBefore, "new exercise resets shot state");
    assert.equal(await page.locator(".sim-ship-card").count(), 3, "shipyard must expose the three blueprint-derived historical vessel classes");
    await page.locator(".sim-ship-card[data-ship=\"iowa\"] details summary").click();
    const iowaDossier = await page.locator(".sim-ship-card[data-ship=\"iowa\"]").innerText();
    assert.ok(iowaDossier.includes("Armor Class") && iowaDossier.includes("320"), "expanded dossier must expose D20 stats and hull integrity");
    await page.locator(".sim-select-attacker[data-ship=\"fletcher\"]").click();
    await page.locator(".sim-select-target[data-ship=\"balao\"]").click();
    assert.match(await page.locator("#sim-combat-selection").innerText(), /Fletcher-class destroyer.*Balao-class submarine/);
    await page.locator("#sim-roll-attack").click();
    assert.match(await page.locator("#sim-combat-log").innerText(), /HIT|MISS|CRITICAL HIT|NATURAL 1/);
    assert.deepEqual(errors, [], "ship roster and D20 combat must not throw uncaught JavaScript errors");

    console.log("VIGIL browser integration: import, marker states, review filters, audit export/clear, Simulation Bay mechanics, manual fleet placement, ship dossiers, D20 combat, runtime errors, and mobile layout passed.");
    await context.close();
  } finally {
    await browser.close();
    await new Promise(resolve => server.close(resolve));
  }
})().catch(error => {
  console.error(error);
  process.exitCode = 1;
});
