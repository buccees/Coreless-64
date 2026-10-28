"""Regression tests for the actual browser-side local decommissioning code.

These run the extracted production JavaScript under Node's built-in VM with a
small event-target stub. They intentionally do not launch a browser or Playwright.
"""
from pathlib import Path
import shutil
import subprocess

import pytest


ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "index.html"


def _run_decommissioning_snippet():
    node = shutil.which("node")
    if not node:
        pytest.skip("Node.js is required for browser lifecycle JavaScript tests")

    html = INDEX.read_text(encoding="utf-8")
    start_marker = "  // Local training decommissioning is an explicit lifecycle transition."
    end_marker = "  window.vigilGetStableWorldEntity=function"
    start = html.find(start_marker)
    end = html.find(end_marker, start)
    assert start >= 0 and end > start, "production decommissioning block must remain discoverable"
    snippet = html[start:end]

    harness = r"""
const assert = require('node:assert/strict');
const vm = require('node:vm');
let regionalWorldSnapshotActive = false;
const regionalTrainingFleet = [
  {id:'UUV-1', unitType:'submersible', x:0.41, y:0.62, afloat:true,
   speed:4, targetSpeed:3, navigationTargetSpeed:2},
  {id:'UUV-BAD', unitType:'submersible', x:2, y:0.5, afloat:true,
   speed:1, targetSpeed:1, navigationTargetSpeed:1}
];
const inventory = [
  {id:'artifact-one', status:'CARRIED', carrierId:'UUV-1'},
  {id:'artifact-two', status:'CARRIED', carrierId:'UUV-1'},
  {id:'artifact-three', status:'AT_SITE', carrierId:null},
  {id:'artifact-other', status:'CARRIED', carrierId:'UUV-OTHER'}
];
const drops = [];
const listeners = {};
const window = {
  addEventListener(name, callback) {
    (listeners[name] ||= []).push(callback);
  },
  dispatchEvent(event) {
    for (const callback of listeners[event.type] || []) callback(event);
    return true;
  },
  vigilGetHistoricalEvidenceInventory() { return inventory; },
  vigilLoseHistoricalEvidence(id, carrierId, x, y) {
    const item = inventory.find(row => row.id === id);
    assert.ok(item, 'only existing artifact records can be dropped');
    assert.equal(item.status, 'CARRIED');
    item.status = 'LOST';
    item.carrierId = null;
    item.location = {x, y};
    drops.push({id, carrierId, x, y});
    return true;
  }
};
class CustomEvent {
  constructor(type, init={}) { this.type = type; this.detail = init.detail; }
}
const context = {window, CustomEvent, regionalTrainingFleet,
                 regionalWorldSnapshotActive};
vm.runInNewContext(require('node:fs').readFileSync(0, 'utf8'), context);
const result = window.vigilDecommissionRegionalUnit('UUV-1');
assert.equal(result.ok, true);
assert.deepEqual(JSON.parse(JSON.stringify(result.position)), {x:0.41, y:0.62});
assert.equal(regionalTrainingFleet[0].afloat, false);
assert.equal(regionalTrainingFleet[0].speed, 0);
assert.equal(regionalTrainingFleet[0].targetSpeed, 0);
assert.equal(regionalTrainingFleet[0].navigationTargetSpeed, 0);
assert.deepEqual(drops, [
  {id:'artifact-one', carrierId:'UUV-1', x:0.41, y:0.62},
  {id:'artifact-two', carrierId:'UUV-1', x:0.41, y:0.62}
]);
assert.equal(inventory.find(row => row.id === 'artifact-three').status, 'AT_SITE');
assert.equal(inventory.find(row => row.id === 'artifact-other').status, 'CARRIED');
assert.equal(window.vigilDecommissionRegionalUnit('UUV-1').ok, false);
assert.equal(drops.length, 2, 'repeat decommissioning must not duplicate drops');
assert.equal(window.vigilDecommissionRegionalUnit('missing').ok, false);
assert.equal(window.vigilDecommissionRegionalUnit('UUV-BAD').ok, false);
context.regionalWorldSnapshotActive = true;
assert.match(window.vigilDecommissionRegionalUnit('UUV-BAD').reason,
             /AUTHORITATIVE SERVER MUST CONFIRM/);
assert.equal(regionalTrainingFleet[1].afloat, true,
             'server-owned units must not be changed by local decommissioning');
console.log('browser decommission lifecycle regression checks passed');
"""
    completed = subprocess.run(
        [node, "-e", harness],
        input=snippet,
        text=True,
        capture_output=True,
        cwd=ROOT,
        check=False,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "browser decommission lifecycle regression checks passed" in completed.stdout


def test_browser_local_decommission_drops_carried_artifacts_once_at_last_position():
    _run_decommissioning_snippet()


def test_local_combat_sinking_invokes_artifact_preserving_decommission():
    node = shutil.which("node")
    if not node:
        pytest.skip("Node.js is required for browser lifecycle JavaScript tests")
    html = INDEX.read_text(encoding="utf-8")
    start_marker = "  var regionalEncounterHistory=[];"
    end_marker = "  function syncRegionalSpeedInput(snapshot)"
    start = html.find(start_marker)
    end = html.find(end_marker, start)
    assert start >= 0 and end > start, "production encounter listener must remain discoverable"
    snippet = html[start:end]
    harness = r"""
const assert = require('node:assert/strict');
const vm = require('node:vm');
const listeners = {};
const regionalTrainingFleet = [
  {id:'UUV-SUNK', unitType:'submersible', x:0.3, y:0.7, afloat:true}
];
const calls = [];
const window = {
  addEventListener(name, callback) { (listeners[name] ||= []).push(callback); },
  vigilDecommissionRegionalUnit(id) { calls.push(id); return {ok:true}; }
};
const document = {getElementById() { return null; }};
const context = {window, document, regionalTrainingFleet};
vm.runInNewContext(require('node:fs').readFileSync(0, 'utf8'), context);
for (const callback of listeners['vigil:regional-encounter'] || []) {
  callback({detail:{sunk:true, source:'local-simulation', target_id:'UUV-SUNK'}});
}
assert.deepEqual(calls, ['UUV-SUNK'], 'local sinking must enter the decommission/drop lifecycle');
for (const callback of listeners['vigil:regional-encounter'] || []) {
  callback({detail:{sunk:true, source:'authoritative-backend', target_id:'UUV-SUNK'}});
}
assert.deepEqual(calls, ['UUV-SUNK'], 'browser must not decommission server-owned units from combat notifications');
console.log('local combat sinking lifecycle integration passed');
"""
    completed = subprocess.run(
        [node, "-e", harness], input=snippet, text=True,
        capture_output=True, cwd=ROOT, check=False,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "local combat sinking lifecycle integration passed" in completed.stdout
