const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const html = fs.readFileSync(path.join(__dirname, "..", "index.html"), "utf8");
const scope = {};
const helperStart = html.indexOf("  // PELAGOS-01 is a stitched spherical surface.");
const helperEndMarker = "  window.vigilAdvancePlanetPoint=vigilAdvancePlanetPoint;";
const helperEnd = html.indexOf(helperEndMarker, helperStart);
assert.ok(helperStart >= 0 && helperEnd > helperStart, "spherical geometry helpers must be embedded in the page");
new Function("window", html.slice(helperStart, helperEnd + helperEndMarker.length))(scope);

const close = (actual, expected, tolerance = 1e-6) => {
  assert.ok(Math.abs(actual - expected) <= tolerance, `expected ${actual} to be within ${tolerance} of ${expected}`);
};
const norm = scope.vigilNormalizePlanetPoint;
const bearing = scope.vigilGetPlanetRangeBearing;
const advance = scope.vigilAdvancePlanetPoint;

close(norm(1.01, 0.5).x, 0.01);
close(norm(-0.01, 0.5).x, 0.99);
const northPoleCrossing = norm(0.25, -0.02);
close(northPoleCrossing.x, 0.75);
close(northPoleCrossing.y, 0.02);
const southPoleCrossing = norm(0.25, 1.02);
close(southPoleCrossing.x, 0.75);
close(southPoleCrossing.y, 0.98);

const seamRange = bearing(0.99, 0.5, 0.01, 0.5);
close(seamRange.distance, 0.04);
close(seamRange.bearing_deg, 90, 1e-5);
const acrossDateLine = advance(0.99, 0.5, 90, 0.02);
assert.ok(Math.min(acrossDateLine.x, 1 - acrossDateLine.x) < 1e-5, "eastbound motion must cross the longitude seam");
const acrossNorthPole = advance(0.25, 0.002, 0, 0.01);
close(acrossNorthPole.x, 0.75, 1e-5);
close(acrossNorthPole.y, 0.008, 1e-5);

const worldStart = html.indexOf("  var VIGIL_WORLD_SEED='PELAGOS-01';");
const worldEndMarker = "window.vigilGetWorldTerrainAt=function(x,y){return vigilWorldAt(Number(x),Number(y));};";
const worldEnd = html.indexOf(worldEndMarker, worldStart);
assert.ok(worldStart >= 0 && worldEnd > worldStart, "seeded spherical terrain generator must be embedded in the page");
const worldScope = {};
new Function("window", html.slice(worldStart, worldEnd + worldEndMarker.length))(worldScope);
const worldAt = worldScope.vigilGetWorldTerrainAt;
const seamA = worldAt(0, 0.37);
const seamB = worldAt(1, 0.37);
close(seamA.depthNorm, seamB.depthNorm, 1e-9);
assert.equal(seamA.isLand, seamB.isLand);
const poleA = worldAt(0.11, 0);
const poleB = worldAt(0.71, 0);
close(poleA.depthNorm, poleB.depthNorm, 1e-6);
assert.equal(poleA.isLand, poleB.isLand);
const overPole = worldAt(0.25, -0.01);
const reflected = worldAt(0.75, 0.01);
close(overPole.depthNorm, reflected.depthNorm, 1e-9);
assert.equal(overPole.isLand, reflected.isLand);

assert.ok(!html.includes("if(ship.x<.04||ship.x>.96)"), "regional fleet must not bounce off horizontal world boundaries");
assert.ok(!html.includes("if(ship.y<.05||ship.y>.95)"), "regional fleet must not bounce off vertical world boundaries");
console.log("Verified wrapped longitude, stitched pole transitions, great-circle bearing/distance, sphere-based movement, and seamless procedural planet terrain.");
