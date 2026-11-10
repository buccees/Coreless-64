(function (root) {
  'use strict';

  var SUBCARRIERS = 64;
  var SAMPLE_RATE_HZ = 20;
  var WINDOW_SIZE = 256;
  var SENSOR_ID = 'WYCF-SCYLLA-001-RFCSI-01';
  var UNIT_ID = 'SCYLLA-001';

  function clamp(value, min, max) { return Math.max(min, Math.min(max, value)); }
  function makeRandom(seed) {
    var state = (Number(seed) >>> 0) || 0x51f15e;
    return function () {
      state ^= state << 13; state ^= state >>> 17; state ^= state << 5;
      return (state >>> 0) / 4294967296;
    };
  }
  function walshSign(subcarrier, channel) {
    return (subcarrier & (1 << channel)) ? -1 : 1;
  }
  function estimateFrequency(values, sampleRate, lowHz, highHz) {
    if (!Array.isArray(values) || values.length < 64) return { hz: null, confidence: 0, power: 0 };
    var mean = values.reduce(function (sum, value) { return sum + value; }, 0) / values.length;
    var centered = values.map(function (value) { return value - mean; });
    var step = sampleRate / (centered.length * 4);
    centered = centered.map(function (value, index) { return value * (0.5 - 0.5 * Math.cos(2 * Math.PI * index / (centered.length - 1))); });
    var best = { hz: null, confidence: 0, power: 0 };
    var totalPower = 0;
    for (var hz = lowHz; hz <= highHz + step * 0.25; hz += step) {
      var re = 0, im = 0;
      for (var i = 0; i < centered.length; i++) {
        var angle = 2 * Math.PI * hz * i / sampleRate;
        re += centered[i] * Math.cos(angle);
        im -= centered[i] * Math.sin(angle);
      }
      var power = (re * re + im * im) / (centered.length * centered.length);
      totalPower += power;
      if (power > best.power) best = { hz: hz, confidence: 0, power: power };
    }
    best.confidence = totalPower > 0 ? clamp(best.power / totalPower, 0, 1) : 0;
    return best;
  }

  function scenarioActors(mode) {
    if (mode === 'empty') return [];
    if (mode === 'single') return [{ id: 'RF-PERSON-01', breathHz: 0.25, heartHz: 1.15, moving: false, phaseOffset: 0.4 }];
    if (mode === 'interference') return [
      { id: 'RF-PERSON-01', breathHz: 0.24, heartHz: 1.12, moving: true, phaseOffset: 0.2 },
      { id: 'RF-PERSON-02', breathHz: 0.31, heartHz: 1.28, moving: false, phaseOffset: 1.1 },
      { id: 'RF-PERSON-03', breathHz: 0.19, heartHz: 0.96, moving: true, phaseOffset: 2.0 }
    ];
    return [
      { id: 'RF-PERSON-01', breathHz: 0.25, heartHz: 1.15, moving: true, phaseOffset: 0.4 },
      { id: 'RF-PERSON-02', breathHz: 0.31, heartHz: 1.28, moving: false, phaseOffset: 1.2 },
      { id: 'RF-PERSON-03', breathHz: 0.19, heartHz: 0.96, moving: true, phaseOffset: 2.1 }
    ];
  }

  function createEngine(options) {
    options = options || {};
    var mode = options.mode || 'multi';
    var random = makeRandom(options.seed || 20261110);
    var actors = scenarioActors(mode).map(function (actor, index) {
      return Object.assign({}, actor, {
        channel: index,
        phaseHistory: [],
        deltaHistory: [],
        previousRawPhase: null,
        unwrappedPhase: 0,
        amplitude: 0.15 + index * 0.012
      });
    });
    var baselineRe = new Float64Array(SUBCARRIERS);
    var baselineIm = new Float64Array(SUBCARRIERS);
    for (var s = 0; s < SUBCARRIERS; s++) {
      baselineRe[s] = 0.58 + 0.08 * Math.cos(s * 0.17);
      baselineIm[s] = 0.04 * Math.sin(s * 0.21);
    }
    var sampleIndex = 0;
    var latest = { tracks: [], presenceCount: 0, movingCount: 0, phaseVariance: 0, sampleCount: 0, quality: 0 };
    var noiseLevel = mode === 'interference' ? 0.006 : 0.0008;

    function step() {
      var time = sampleIndex / SAMPLE_RATE_HZ;
      var currentRe = new Float64Array(SUBCARRIERS);
      var currentIm = new Float64Array(SUBCARRIERS);
      for (var k = 0; k < SUBCARRIERS; k++) {
        currentRe[k] = baselineRe[k];
        currentIm[k] = baselineIm[k];
      }
      actors.forEach(function (actor) {
        var respiration = 0.035 * Math.sin(2 * Math.PI * actor.breathHz * time + actor.phaseOffset);
        var heartbeat = 0.009 * Math.sin(2 * Math.PI * actor.heartHz * time + actor.phaseOffset * 1.7);
        var grossMotion = actor.moving ? 0.14 * Math.sin(2 * Math.PI * 0.625 * time + actor.phaseOffset * 0.6) : 0;
        var phase = respiration + heartbeat + grossMotion;
        var amp = actor.amplitude * (1 + 0.025 * Math.sin(2 * Math.PI * 0.07 * time + actor.phaseOffset));
        for (var sub = 0; sub < SUBCARRIERS; sub++) {
          var sign = walshSign(sub, actor.channel);
          currentRe[sub] += amp * sign * Math.cos(phase);
          currentIm[sub] += amp * sign * Math.sin(phase);
        }
      });
      for (var n = 0; n < SUBCARRIERS; n++) {
        currentRe[n] += (random() - 0.5) * noiseLevel;
        currentIm[n] += (random() - 0.5) * noiseLevel;
      }

      var tracks = [];
      var phaseDeltas = [];
      actors.forEach(function (actor) {
        var projectionRe = 0, projectionIm = 0;
        for (var j = 0; j < SUBCARRIERS; j++) {
          var sign = walshSign(j, actor.channel);
          projectionRe += (currentRe[j] - baselineRe[j]) * sign;
          projectionIm += (currentIm[j] - baselineIm[j]) * sign;
        }
        projectionRe /= SUBCARRIERS;
        projectionIm /= SUBCARRIERS;
        var amplitude = Math.hypot(projectionRe, projectionIm);
        var rawPhase = Math.atan2(projectionIm, projectionRe);
        if (actor.previousRawPhase === null) actor.unwrappedPhase = rawPhase;
        else {
          var delta = rawPhase - actor.previousRawPhase;
          while (delta > Math.PI) delta -= 2 * Math.PI;
          while (delta < -Math.PI) delta += 2 * Math.PI;
          actor.unwrappedPhase += delta;
          actor.deltaHistory.push(delta);
          if (actor.deltaHistory.length > 80) actor.deltaHistory.shift();
          phaseDeltas.push(delta);
        }
        actor.previousRawPhase = rawPhase;
        actor.phaseHistory.push(actor.unwrappedPhase);
        if (actor.phaseHistory.length > WINDOW_SIZE) actor.phaseHistory.shift();
        var presence = clamp(amplitude / 0.075, 0, 1);
        var motionRms = actor.deltaHistory.length ? Math.sqrt(actor.deltaHistory.reduce(function (sum, value) { return sum + value * value; }, 0) / actor.deltaHistory.length) : 0;
        var isPresent = presence >= 0.28;
        if (isPresent) {
          if (sampleIndex % SAMPLE_RATE_HZ === 0 && actor.phaseHistory.length >= 64) {
            actor.breathEstimate = estimateFrequency(actor.phaseHistory, SAMPLE_RATE_HZ, 0.1, 0.5);
            actor.pulseEstimate = estimateFrequency(actor.phaseHistory, SAMPLE_RATE_HZ, 0.8, 2.0);
          }
          var breath = actor.breathEstimate || { hz: null, confidence: 0 };
          var pulse = actor.pulseEstimate || { hz: null, confidence: 0 };
          tracks.push({
            id: actor.id,
            classification: 'SYNTHETIC HUMAN-PRESENCE CHANNEL',
            presence: presence,
            movement: motionRms > 0.014 ? 'MOVING' : 'STATIONARY',
            movementScore: clamp(motionRms / 0.05, 0, 1),
            breathingBpm: breath.hz === null ? null : breath.hz * 60,
            breathingConfidence: breath.confidence,
            heartRateBpm: pulse.hz === null ? null : pulse.hz * 60,
            heartRateConfidence: pulse.confidence,
            confidence: clamp(presence * (0.55 + 0.45 * (1 - noiseLevel / 0.02)), 0, 1),
            samples: actor.phaseHistory.length,
            phaseTrace: actor.phaseHistory.slice(-128)
          });
        }
      });
      sampleIndex++;
      var phaseVariance = phaseDeltas.length ? phaseDeltas.reduce(function (sum, value) { return sum + value * value; }, 0) / phaseDeltas.length : 0;
      latest = {
        tracks: tracks,
        presenceCount: tracks.length,
        movingCount: tracks.filter(function (track) { return track.movement === 'MOVING'; }).length,
        phaseVariance: phaseVariance,
        sampleCount: sampleIndex,
        quality: clamp(1 - noiseLevel / 0.025, 0, 1)
      };
      return snapshot();
    }
    function snapshot() {
      return {
        mode: mode,
        sampleRateHz: SAMPLE_RATE_HZ,
        subcarriers: SUBCARRIERS,
        sampleCount: latest.sampleCount,
        tracks: latest.tracks.map(function (track) { return Object.assign({}, track); }),
        presenceCount: latest.presenceCount,
        movingCount: latest.movingCount,
        phaseVariance: latest.phaseVariance,
        quality: latest.quality,
        vitalsReady: sampleIndex >= WINDOW_SIZE,
        provenance: 'SOFTWARE-GENERATED SYNTHETIC CSI // NO RADIO OR HARDWARE INPUT'
      };
    }
    return { step: step, snapshot: snapshot, sampleRateHz: SAMPLE_RATE_HZ, subcarriers: SUBCARRIERS, mode: mode };
  }

  function toSensorFrame(snapshot) {
    var breathValues = snapshot.tracks.filter(function (track) { return track.breathingBpm !== null; }).map(function (track) { return track.breathingBpm; });
    var pulseValues = snapshot.tracks.filter(function (track) { return track.heartRateBpm !== null; }).map(function (track) { return track.heartRateBpm; });
    return {
      schema: 'vigil.fleet.sensor-frame', version: 1,
      unit_id: UNIT_ID, unit_name: 'WEYLAND-YUTANI // CORPORATE SECURITY',
      unit_profile: 'security', sensor_id: SENSOR_ID,
      sensor_name: 'SOFTWARE-DEFINED CSI / RF PRESENCE ARRAY', modality: 'wifi_csi',
      provenance: snapshot.provenance,
      measurements: [
        { label: 'CSI SUBCARRIERS', value: SUBCARRIERS, units: 'tones' },
        { label: 'SAMPLE RATE', value: SAMPLE_RATE_HZ, units: 'Hz' },
        { label: 'PRESENCE CHANNELS', value: snapshot.presenceCount, units: 'tracks' },
        { label: 'MOVING CHANNELS', value: snapshot.movingCount, units: 'tracks' },
        { label: 'PHASE VARIANCE', value: snapshot.phaseVariance, units: 'rad²' },
        { label: 'MEAN BREATH ESTIMATE', value: breathValues.length ? breathValues.reduce(function (a, b) { return a + b; }, 0) / breathValues.length : 0, units: 'breaths/min' },
        { label: 'MEAN HEART-RATE ESTIMATE', value: pulseValues.length ? pulseValues.reduce(function (a, b) { return a + b; }, 0) / pulseValues.length : 0, units: 'beats/min' },
        { label: 'SIGNAL QUALITY', value: snapshot.quality, units: 'normalized' },
        { label: 'DATA ORIGIN', value: 'SYNTHETIC CSI', units: 'software test' }
      ].concat(snapshot.tracks.reduce(function (rows, track) {
        rows.push(
          { label: track.id + ' // PRESENCE', value: track.presence, units: 'normalized' },
          { label: track.id + ' // MOVEMENT', value: track.movement, units: 'classification' },
          { label: track.id + ' // BREATHING', value: track.breathingBpm === null ? 'WARMING' : track.breathingBpm, units: 'breaths/min' },
          { label: track.id + ' // HEART RATE', value: track.heartRateBpm === null ? 'WARMING' : track.heartRateBpm, units: 'beats/min' },
          { label: track.id + ' // CONFIDENCE', value: track.confidence, units: 'normalized' }
        );
        return rows;
      }, [])),
      detected_contacts: snapshot.tracks.map(function (track) {
        return { contact_id: track.id, classification: track.classification, confidence: track.confidence };
      }),
      timestamp: new Date().toISOString()
    };
  }

  var api = {
    schema: 'vigil.software-rf-sensing',
    version: 1,
    createEngine: createEngine,
    estimateFrequency: estimateFrequency,
    toSensorFrame: toSensorFrame,
    constants: { subcarriers: SUBCARRIERS, sampleRateHz: SAMPLE_RATE_HZ, windowSize: WINDOW_SIZE }
  };
  if (root) root.vigilRFSensingLab = api;
  if (typeof document === 'undefined') return;

  var panel = document.getElementById('wy-rf-sensing');
  if (!panel) return;
  var startButton = panel.querySelector('#wy-rf-start');
  var pauseButton = panel.querySelector('#wy-rf-pause');
  var resetButton = panel.querySelector('#wy-rf-reset');
  var scenarioSelect = panel.querySelector('#wy-rf-scenario');
  var status = panel.querySelector('#wy-rf-status');
  var trackList = panel.querySelector('#wy-rf-tracks');
  var presenceStat = panel.querySelector('#wy-rf-presence');
  var movingStat = panel.querySelector('#wy-rf-moving');
  var qualityStat = panel.querySelector('#wy-rf-quality');
  var samplesStat = panel.querySelector('#wy-rf-samples');
  var expandButton = panel.querySelector('#wy-rf-expand');
  var phaseCanvas = panel.querySelector('#wy-rf-phase');
  var phaseContext = phaseCanvas && phaseCanvas.getContext ? phaseCanvas.getContext('2d') : null;
  var engine = createEngine({ mode: scenarioSelect ? scenarioSelect.value : 'multi' });
  var timer = null;
  var lastPublishAt = 0;

  function drawPhase(snapshot) {
    if (!phaseContext || !phaseCanvas) return;
    var width = phaseCanvas.width, height = phaseCanvas.height;
    phaseContext.clearRect(0, 0, width, height);
    phaseContext.fillStyle = '#020b08'; phaseContext.fillRect(0, 0, width, height);
    phaseContext.strokeStyle = '#173e2b'; phaseContext.lineWidth = 1;
    for (var y = 1; y < 4; y++) { phaseContext.beginPath(); phaseContext.moveTo(0, y * height / 4); phaseContext.lineTo(width, y * height / 4); phaseContext.stroke(); }
    var tracks = snapshot.tracks;
    if (!tracks.length) {
      phaseContext.fillStyle = '#789985'; phaseContext.font = '12px monospace';
      phaseContext.fillText('NO PRESENCE SIGNATURES ABOVE THRESHOLD', 12, height / 2);
      return;
    }
    tracks.forEach(function (track, index) {
      var color = ['#8cffb6', '#79d8ff', '#e5c77d'][index % 3];
      phaseContext.strokeStyle = color; phaseContext.lineWidth = 1.5; phaseContext.beginPath();
      var values = track.phaseTrace || [];
      if (values.length < 2) return;
      values.forEach(function (value, point) {
        var x = point / (values.length - 1) * width;
        var y = height / 2 - clamp(value * 18, -height * 0.42, height * 0.42);
        if (point === 0) phaseContext.moveTo(x, y); else phaseContext.lineTo(x, y);
      });
      phaseContext.stroke();
    });
  }

  function render(snapshot) {
    if (presenceStat) presenceStat.textContent = String(snapshot.presenceCount).padStart(2, '0');
    if (movingStat) movingStat.textContent = String(snapshot.movingCount).padStart(2, '0');
    if (qualityStat) qualityStat.textContent = (snapshot.quality * 100).toFixed(0) + '%';
    if (samplesStat) samplesStat.textContent = String(snapshot.sampleCount);
    if (status) status.textContent = 'SOFTWARE CSI // ' + snapshot.sampleCount + ' SAMPLES // ' + snapshot.presenceCount + ' PRESENCE CHANNEL(S) // ' + (snapshot.vitalsReady ? 'VITALS ESTIMATED' : 'VITALS WINDOW WARMING');
    if (trackList) {
      trackList.textContent = '';
      if (!snapshot.tracks.length) {
        var empty = document.createElement('div'); empty.className = 'wy-rf-empty';
        empty.textContent = 'NO PRESENCE DETECTED // SIMULATED ROOM CHANNEL'; trackList.appendChild(empty);
      }
      snapshot.tracks.forEach(function (track) {
        var card = document.createElement('article'); card.className = 'wy-rf-track';
        var title = document.createElement('strong'); title.textContent = track.id + ' // ' + track.movement;
        var details = document.createElement('small');
        var breath = track.breathingBpm === null ? 'WARMING' : track.breathingBpm.toFixed(0) + ' BPM';
        var pulse = track.heartRateBpm === null ? 'WARMING' : track.heartRateBpm.toFixed(0) + ' BPM';
        details.textContent = 'PRESENCE ' + (track.presence * 100).toFixed(0) + '% // BREATH ' + breath + ' // HEART ' + pulse + ' // CONFIDENCE ' + (track.confidence * 100).toFixed(0) + '%';
        card.appendChild(title); card.appendChild(details); trackList.appendChild(card);
      });
    }
    drawPhase(snapshot);
  }

  function publish(snapshot) {
    if (!root || typeof root.vigilRecordUnitSensorFeed !== 'function') return;
    root.vigilRecordUnitSensorFeed(toSensorFrame(snapshot));
  }

  function stepBatch() {
    var snapshot;
    for (var i = 0; i < 5; i++) snapshot = engine.step();
    render(snapshot);
    var now = Date.now();
    if (now - lastPublishAt >= 2000) { publish(snapshot); lastPublishAt = now; }
  }
  function stop() {
    if (timer !== null) { root.clearInterval(timer); timer = null; }
    if (pauseButton) pauseButton.disabled = true;
    if (startButton) startButton.disabled = false;
  }
  function start() {
    if (timer !== null) return;
    if (startButton) startButton.disabled = true;
    if (pauseButton) pauseButton.disabled = false;
    if (status) status.textContent = 'STARTING SOFTWARE-ONLY CSI SCENARIO // NO HARDWARE';
    timer = root.setInterval(stepBatch, 250);
  }
  function reset() {
    stop();
    engine = createEngine({ mode: scenarioSelect ? scenarioSelect.value : 'multi' });
    lastPublishAt = 0;
    render(engine.snapshot());
    if (status) status.textContent = 'RESET COMPLETE // ' + String(engine.mode).toUpperCase() + ' SCENARIO READY';
  }
  if (expandButton) expandButton.addEventListener('click', function () {
    var expanded = panel.classList.toggle('wy-rf-expanded');
    expandButton.setAttribute('aria-pressed', String(expanded));
    expandButton.textContent = expanded ? 'CLOSE COCKPIT DISPLAY' : 'OPEN COCKPIT DISPLAY';
  });
  if (startButton) startButton.addEventListener('click', start);
  if (pauseButton) pauseButton.addEventListener('click', stop);
  if (resetButton) resetButton.addEventListener('click', reset);
  if (scenarioSelect) scenarioSelect.addEventListener('change', reset);
  if (pauseButton) pauseButton.disabled = true;
  render(engine.snapshot());
})(typeof window !== 'undefined' ? window : null);
