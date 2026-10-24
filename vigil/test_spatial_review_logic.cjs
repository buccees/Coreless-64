#!/usr/bin/env node
"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

// Execute the production browser function with a minimal DOM stub. This tests
// classification behavior, not full browser interaction.
const html = fs.readFileSync(path.join(__dirname, "..", "index.html"), "utf8");
const signature = "function updateEvidenceBridge(data) {";
const start = html.indexOf(signature);
assert.notEqual(start, -1, "updateEvidenceBridge must exist");
let depth = 0, quote = null, escaped = false, end = -1;
for (let i = start + signature.length - 1; i < html.length; i += 1) {
  const ch = html[i];
  if (quote) {
    if (escaped) escaped = false;
    else if (ch.charCodeAt(0) === 92) escaped = true;
    else if (ch === quote) quote = null;
    continue;
  }
  if (ch === "'" || ch === '"') quote = ch;
  else if (ch === "{") depth += 1;
  else if (ch === "}" && --depth === 0) { end = i + 1; break; }
}
assert.notEqual(end, -1, "function body must be balanced");
const productionFunction = html.slice(start, end);
const ids = [
  "bridge-scene-state", "bridge-track-count", "bridge-stable-count",
  "bridge-review-count", "bridge-source-state", "bridge-hardware-state",
  "bridge-conflict-count", "bridge-uncertainty-count",
  "bridge-calibration-count", "bridge-lineage-count", "bridge-scene-detail"
];
function runBridge(data) {
  const nodes = Object.create(null);
  for (const id of ids) nodes[id] = { textContent: "" };
  const context = { document: { getElementById: id => nodes[id] || null }, Object, Array, String, Number };
  vm.runInNewContext(productionFunction, context);
  context.updateEvidenceBridge(data);
  return nodes;
}
function track(overrides = {}) {
  return Object.assign({
    object_id: "T-1", uncertainty_m: 0.5, calibration_status: "verified",
    lineage_declared: true, conflict: false, modalities: [], sensor_ids: []
  }, overrides);
}
// Exactly 1 m is accepted; only values greater than 1 m trigger the gate.
{
  const n = runBridge({ model_id: "test", revision: "1", frame_id: "local", objects: [track({ uncertainty_m: 1 })] });
  assert.equal(n["bridge-track-count"].textContent, "1");
  assert.equal(n["bridge-stable-count"].textContent, "1");
  assert.equal(n["bridge-review-count"].textContent, "0");
  assert.equal(n["bridge-uncertainty-count"].textContent, "0");
}
// Above-threshold uncertainty.
{
  const n = runBridge({ objects: [track({ uncertainty_m: 1.01 })] });
  assert.equal(n["bridge-review-count"].textContent, "1");
  assert.equal(n["bridge-uncertainty-count"].textContent, "1");
}
// Missing uncertainty cannot silently pass.
{
  const n = runBridge({ objects: [track({ uncertainty_m: undefined })] });
  assert.equal(n["bridge-review-count"].textContent, "1");
  assert.equal(n["bridge-uncertainty-count"].textContent, "1");
}
// Calibration and lineage are independently counted.
{
  const n = runBridge({ objects: [track({ calibration_status: "unverified", lineage_declared: false })] });
  assert.equal(n["bridge-review-count"].textContent, "1");
  assert.equal(n["bridge-calibration-count"].textContent, "1");
  assert.equal(n["bridge-lineage-count"].textContent, "1");
}
// Explicit conflict.
{
  const n = runBridge({ objects: [track({ conflict: true })] });
  assert.equal(n["bridge-review-count"].textContent, "1");
  assert.equal(n["bridge-conflict-count"].textContent, "1");
}
// Mixed data verifies aggregate totals and overlapping gate counts.
{
  const n = runBridge({ objects: [
    track(), track({ conflict: true }), track({ uncertainty_m: null }),
    track({ calibration_status: "pending" }), track({ lineage_declared: false })
  ] });
  assert.equal(n["bridge-track-count"].textContent, "5");
  assert.equal(n["bridge-stable-count"].textContent, "1");
  assert.equal(n["bridge-review-count"].textContent, "4");
  assert.equal(n["bridge-conflict-count"].textContent, "1");
  assert.equal(n["bridge-uncertainty-count"].textContent, "1");
  assert.equal(n["bridge-calibration-count"].textContent, "1");
  assert.equal(n["bridge-lineage-count"].textContent, "1");
}
console.log("VIGIL spatial review logic: 6 scenario groups passed.");


// Shared extractor for additional production functions embedded in index.html.
function extractFunction(signature) {
  const start = html.indexOf(signature);
  assert.notEqual(start, -1, signature + " must exist");
  let depth = 0, quote = null, escaped = false, end = -1;
  for (let i = start + signature.length - 1; i < html.length; i += 1) {
    const ch = html[i];
    if (quote) {
      if (escaped) escaped = false;
      else if (ch.charCodeAt(0) === 92) escaped = true;
      else if (ch === quote) quote = null;
      continue;
    }
    if (ch === "'" || ch === '"') quote = ch;
    else if (ch === "{") depth += 1;
    else if (ch === "}" && --depth === 0) { end = i + 1; break; }
  }
  assert.notEqual(end, -1, signature + " body must be balanced");
  return html.slice(start, end);
}
function makeNode(tag) {
  return {
    tag, textContent: "", style: {}, attributes: {}, children: [], parentNode: null,
    appendChild(child) { child.parentNode = this; this.children.push(child); return child; },
    removeChild(child) { this.children.splice(this.children.indexOf(child), 1); child.parentNode = null; return child; },
    get firstChild() { return this.children[0] || null; },
    setAttribute(name, value) { this.attributes[name] = String(value); },
    getAttribute(name) { return this.attributes[name] || ""; }
  };
}
function treeText(node) {
  return [node.textContent].concat(node.children.map(treeText)).join(" ");
}

// Track inspector tests exercise the actual production inspector and its four
// independent gate explanations, with a small DOM tree rather than a browser.
{
  const detail = makeNode("section");
  const level = { value: "all" };
  const context = {
    document: { createElement: makeNode, createTextNode: text => Object.assign(makeNode("#text"), { textContent: text }) },
    spatialTrackDetail: detail, spatialLevel: level,
    recordSpatialAudit: () => {}, spatialReviewDecisionKey: object => String(object.object_id || 'OBJECT'),
    finite3: point => Array.isArray(point) && point.length >= 3 &&
      point.slice(0, 3).every(n => typeof n === "number" && Number.isFinite(n)),
    Array, Number, String, Math, Object
  };
  vm.runInNewContext(extractFunction("function inspectSpatialTrack(object, suppressAudit) {"), context);
  context.inspectSpatialTrack({
    object_id: "T-42", inferred_level: "2",
    motion_trail_m: [[1, [0, 1, 1]], [2, [0, 2, 4]]],
    floor_transitions: [{ from_level: "1", to_level: "2", timestamp_ns: 123 }],
    uncertainty_m: 1.2, observation_count: 3, sensor_ids: ["LIDAR-A"],
    independence_groups: ["optical"], modalities: ["lidar"],
    conflict: true, conflict_reasons: ["range disagreement"],
    conflicting_sensor_ids: ["LIDAR-B"], calibration_status: "pending",
    lineage_declared: false
  });
  const text = treeText(detail);
  assert.match(text, /TRACK INSPECTOR \/\/ T-42 \/\/ LEVEL 2/);
  assert.match(text, /1\.00–4\.00 m Z/);
  assert.match(text, /Position uncertainty/);
  assert.match(text, /REVIEW REQUIRED \(4\/4\)/);
  for (const gate of ["CONFLICT", "UNCERTAINTY", "CALIBRATION", "LINEAGE"]) {
    assert.match(text, new RegExp(gate));
  }
  assert.match(text, /range disagreement/);
  assert.match(text, /DO NOT CONFIRM/);
  // Missing values are described as unknown rather than silently accepted.
  detail.children = [];
  context.inspectSpatialTrack({ object_id: "T-MISSING", uncertainty_m: NaN });
  const missingText = treeText(detail);
  assert.match(missingText, /Position uncertainty UNKNOWN/);
  assert.match(missingText, /REVIEW REQUIRED \(3\/4\)/);
}

// Filter tests verify the real filter function dims non-matching markers,
// keeps missing calibration/lineage under the "missing" filter, and updates
// accessible button state plus the current status attribute.
{
  const filters = ["all", "conflict", "uncertainty", "missing"].map(value => {
    const node = makeNode("button"); node.setAttribute("data-review-filter", value); return node;
  });
  const markers = [
    { flags: "conflict", style: {} },
    { flags: "uncertainty", style: {} },
    { flags: "calibration-review", style: {} },
    { flags: "lineage-unknown", style: {} },
    { flags: "", style: {} }
  ].map(item => ({
    style: item.style, getAttribute: name => name === "data-review-flags" ? item.flags : ""
  }));
  const stage = { querySelectorAll: selector => selector === "[data-review-flags]" ? markers : [] };
  const status = makeNode("div");
  const context = { spatialReviewFilters: filters, spatialStatus: status, spatialStage: stage, Array, String };
  vm.runInNewContext(extractFunction("function applySpatialReviewFilter(filter) {"), context);
  context.applySpatialReviewFilter("missing");
  assert.deepEqual(markers.map(m => m.style.opacity), [".12", ".12", "1", "1", ".12"]);
  assert.equal(status.attributes["data-review-filter"], "missing");
  assert.deepEqual(filters.map(b => b.attributes["aria-pressed"]), ["false", "false", "false", "true"]);
  context.applySpatialReviewFilter("conflict");
  assert.deepEqual(markers.map(m => m.style.opacity), ["1", ".12", ".12", ".12", ".12"]);
  assert.deepEqual(filters.map(b => b.attributes["aria-pressed"]), ["false", "true", "false", "false"]);
  context.applySpatialReviewFilter("all");
  assert.deepEqual(markers.map(m => m.style.opacity), ["1", "1", "1", "1", "1"]);
}
console.log("VIGIL track inspector and review filters: 2 scenario groups passed.");
