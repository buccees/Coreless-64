"""Regression checks for the standalone browser operator display.

These tests guard important client-side contracts without pretending to be a
full real-browser integration test; hosted endpoint verification remains a
deployment checkpoint.
"""
from pathlib import Path


PAGE = Path(__file__).resolve().parents[1] / "operator-display.html"


def test_browser_timestamp_validator_is_shared_by_validation_and_rendering():
    source = PAGE.read_text(encoding="utf-8")
    assert "function validNs(value)" in source
    assert "if(!validNs(data.generated_at_ns)||!validNs(data.source_timestamp_ns))" in source
    assert "validNs(sensor.source_timestamp_ns)" in source
    # The validator must be outside validate(), since rendering calls it too.
    assert source.index("function validNs(value)") < source.index("function validate(data)")
    assert source.index("function validate(data)") < source.index("function render(data)")


def test_browser_rejects_endpoint_urls_that_could_hide_credentials():
    source = PAGE.read_text(encoding="utf-8")
    assert "url.protocol!=='https:'" in source
    assert "url.username||url.password||url.hash||url.search" in source
    assert "credentials:'include'" in source
    assert "cache:'no-store'" in source
    assert "redirect:'error'" in source


def test_browser_renders_untrusted_runtime_strings_as_text_not_html():
    source = PAGE.read_text(encoding="utf-8")
    assert "el.textContent=String(value)" in source
    assert "innerHTML" not in source


def test_browser_display_remains_read_only_and_has_connection_lifecycle_controls():
    source = PAGE.read_text(encoding="utf-8")
    assert "method:'GET'" in source
    assert "id=\"connect\"" in source
    assert "id=\"disconnect\"" in source
    assert "function stopConnection(message)" in source
    assert "window.addEventListener('pagehide'" in source
