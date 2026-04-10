from core.runes import RUNES, rune_for_status, rune_log


def test_minimal_rune_count_and_required_keys() -> None:
    assert 5 <= len(RUNES) <= 8
    assert {"input", "flow", "transform", "split", "output", "error", "lock"}.issubset(RUNES)


def test_rune_svgs_are_embedded_and_sharp() -> None:
    for rune in RUNES.values():
        assert rune.svg.startswith("<svg")
        assert "stroke-linecap=\"square\"" in rune.svg
        assert "path" in rune.svg or "rect" in rune.svg


def test_status_mapping_and_log_format() -> None:
    assert rune_for_status("SUCCESS").key == "output"
    assert rune_for_status("PROCESSING_ERROR").key == "error"
    line = rune_log("transform", "PROCESSING")
    assert line.startswith("[")
    assert "PROCESSING" in line
