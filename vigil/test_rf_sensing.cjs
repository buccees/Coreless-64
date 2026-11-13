'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const sourcePath = path.join(__dirname, '..', 'vigil-rf-sensing.js');
const context = { window: {}, console, Math, Date, Float64Array, Array, Object, Number, String };
vm.createContext(context);
vm.runInContext(fs.readFileSync(sourcePath, 'utf8'), context);
const api = context.window.vigilRFSensingLab;
assert.equal(api.schema, 'vigil.software-rf-sensing');
assert.equal(api.constants.subcarriers, 64);

function runScenario(mode, seed, count) {
  const engine = api.createEngine({ mode, seed });
  let snapshot;
  for (let i = 0; i < count; i++) snapshot = engine.step();
  return snapshot;
}

const multi = runScenario('multi', 1234, 320);
assert.equal(multi.presenceCount, 3, 'multi-person scenario should separate three synthetic channels');
assert.equal(multi.tracks.length, 3);
assert.ok(multi.vitalsReady);
const expected = [
  { breath: 15, heart: 69 },
  { breath: 19, heart: 77 },
  { breath: 11, heart: 58 }
];
multi.tracks.forEach((track, index) => {
  assert.ok(Math.abs(track.breathingBpm - expected[index].breath) < 2.5, track.id + ' breathing estimate ' + track.breathingBpm);
  assert.ok(Math.abs(track.heartRateBpm - expected[index].heart) < 4, track.id + ' heart estimate ' + track.heartRateBpm);
  assert.ok(track.confidence > 0.5);
});
assert.ok(multi.movingCount >= 1, 'moving targets should be classified');
const frame = api.toSensorFrame(multi);
assert.equal(frame.unit_id, 'SCYLLA-001');
assert.equal(frame.modality, 'wifi_csi');
assert.match(frame.provenance, /SYNTHETIC CSI/);
assert.equal(frame.detected_contacts.length, 3);
assert.ok(frame.detected_contacts.every(contact => !('normalized_position' in contact)), 'CSI-only evidence must not invent coordinates');

const empty = runScenario('empty', 1234, 100);
assert.equal(empty.presenceCount, 0, 'empty room should not generate presence detections');
const single = runScenario('single', 1234, 300);
assert.equal(single.presenceCount, 1);
assert.equal(single.tracks[0].movement, 'STATIONARY');
const interference = runScenario('interference', 99, 320);
assert.equal(interference.presenceCount, 3, 'interference scenario should retain separated synthetic channels');
assert.ok(interference.quality < multi.quality, 'interference should lower signal quality');
const frequency = api.estimateFrequency(Array.from({ length: 256 }, (_, i) => Math.sin(2 * Math.PI * 1.25 * i / 20)), 20, 0.8, 2);
assert.ok(Math.abs(frequency.hz - 1.25) <= 20 / 256, 'frequency estimator error ' + frequency.hz);

const html = fs.readFileSync(path.join(__dirname, '..', 'index.html'), 'utf8');
assert.ok(html.includes('id="wy-rf-sensing"'), 'RF sensing display must be mounted in the existing Security Cockpit');
assert.ok(/vigil-rf-sensing\.js\?v=\d+&build=/.test(html), 'Security Cockpit must load the RF sensing engine with cache busting');
console.log('VIGIL software RF sensing: synthetic multi-person separation, presence, motion, respiration/heart-rate estimation, interference degradation, empty-room rejection, shared sensor frame contract and Security Cockpit integration passed.');
