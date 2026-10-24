"""Source-contract regression tests for the VIGIL single-file spatial UI.

These checks protect the browser-side import/review contract without pretending to
replace browser interaction tests. They intentionally inspect production source.
"""
from pathlib import Path
import re

INDEX = Path(__file__).resolve().parents[1] / "index.html"
SOURCE = INDEX.read_text(encoding="utf-8")


def function_body(name: str) -> str:
    """Return a function body using brace counting while ignoring JS strings."""
    match = re.search(r"function\s+" + re.escape(name) + r"\s*\([^)]*\)\s*\{", SOURCE)
    assert match, f"Missing production function: {name}"
    start = match.end()
    depth = 1
    quote = None
    escaped = False
    i = start
    while i < len(SOURCE):
        char = SOURCE[i]
        if quote:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = None
        elif char in ("'", '"', "`"):
            quote = char
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return SOURCE[start:i]
        i += 1
    raise AssertionError(f"Unclosed function body: {name}")


def test_import_requires_blueprintview_envelope():
    body = SOURCE[SOURCE.index("JSON.parse(String(reader.result || '')"):]
    validation = body[:body.index("importedScene = data;")]
    for required in (
        "typeof data.model_id !== 'string'",
        "typeof data.revision !== 'string'",
        "typeof data.frame_id !== 'string'",
        "!Array.isArray(data.features)",
        "!Array.isArray(data.objects)",
    ):
        assert required in validation


def test_rejected_json_clears_scene_and_evidence_bridge():
    body = SOURCE[SOURCE.index("JSON.parse(String(reader.result || '')"):]
    catch = body[body.index("} catch (error) {"):body.index("reader.readAsText(file)")]
    assert "importedScene = null;" in catch
    assert "updateEvidenceBridge(null);" in catch
    assert "clearImportedLayers();" in catch
    assert "IMPORT REJECTED //" in catch


def test_reader_error_clears_scene_and_evidence_bridge():
    body = SOURCE[SOURCE.index("reader.onerror = function()"):]
    handler = body[:body.index("reader.readAsText(file)")]
    assert "importedScene = null;" in handler
    assert "updateEvidenceBridge(null);" in handler
    assert "clearImportedLayers();" in handler
    assert "IMPORT FAILED // FILE COULD NOT BE READ" in handler


def test_bridge_counts_all_four_independent_review_gates():
    body = function_body("updateEvidenceBridge")
    for rule in (
        "object.conflict === true",
        "!uncertaintyKnown || uncertainty > 1",
        "calibration !== 'verified'",
        "object.lineage_declared !== true",
    ):
        assert rule in body
    assert "var needsReview = hasConflict || hasUncertaintyFlag || hasCalibrationFlag || hasLineageFlag;" in body


def test_track_inspector_explains_each_gate():
    body = function_body("inspectSpatialTrack")
    for gate in ("CONFLICT", "UNCERTAINTY", "CALIBRATION", "LINEAGE"):
        assert "name:'" + gate + "'" in body
    assert "INDEPENDENT REVIEW GATES" in body
    assert "textContent" in body


def test_review_filters_include_unverified_calibration_and_lineage():
    body = function_body("applySpatialReviewFilter")
    assert "flags.indexOf('calibration-review')" in body
    assert "flags.indexOf('lineage-unknown')" in body
    assert "data-review-flags" in body


def test_html_ids_are_unique():
    ids = re.findall(r'\bid=["\']([^"\']+)["\']', SOURCE)
    duplicates = sorted({item for item in ids if ids.count(item) > 1})
    assert not duplicates, f"Duplicate HTML IDs: {duplicates}"


def test_spatial_markers_distinguish_unknown_uncertainty_and_metadata_review():
    body = function_body("renderImportedScene")
    assert "!uncertaintyKnown ? ' uncertainty-unknown' : ''" in body
    assert "calibrationUnverified || !lineageDeclared ? ' metadata-review' : ''" in body
    assert ".imported-object.uncertainty-unknown:not(.conflict)" in SOURCE
    assert ".imported-object.metadata-review:not(.conflict):not(.uncertainty-unknown)" in SOURCE
    assert "UNKNOWN UNCERTAINTY / AMBER DASHED" in SOURCE
    assert "BLUE DASHED OUTLINE / CALIBRATION OR LINEAGE REVIEW" in SOURCE


def test_spatial_audit_records_review_decisions_with_reasons_and_bounds_history():
    recorder = function_body("recordSpatialAudit")
    saver = function_body("saveSpatialTrackReviewDecision")
    assert "new Date().toISOString()" in recorder
    assert "spatialAuditEntries.length > 100" in recorder
    assert "localStorage.setItem(spatialAuditStorageKey" in recorder
    assert "if (!explanation)" in saver
    assert "TRACK REVIEW DECISION" in saver
    assert "spatialReviewDecisionStorageKey" in SOURCE
    assert "NOT TAMPER-PROOF" in SOURCE
    assert 'id="spatial-audit-list"' in SOURCE
    assert 'id="spatial-audit-export"' in SOURCE


def test_successful_scene_import_binds_markers_and_refreshes_review_controls():
    source = SOURCE
    import_handler = source[source.index("reader.onload = function() {"):source.index("reader.onerror = function() {")]
    assert "var counts = renderImportedScene(data);" in import_handler
    assert "applyImportedLevelFilter();" in import_handler
    assert "applySpatialReviewFilter(spatialReviewFilter);" in import_handler
    assert "bindSpatialTrackInspection(importedScene);" in import_handler
    assert "updateCsiAssociation(importedScene);" in import_handler
