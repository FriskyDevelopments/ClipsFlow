import os

import pytest

from core.config import parsers


def _clear_env(var_names):
    for name in var_names:
        os.environ.pop(name, None)


class TestParseIntEnv:
    def test_invalid_int_raises(self, monkeypatch):
        monkeypatch.setenv("TEST_INT", "abc")
        with pytest.raises(ValueError) as excinfo:
            parsers.parse_int_env("TEST_INT", default=1)
        assert "[CONFIG ERROR]" in str(excinfo.value)
        assert "TEST_INT" in str(excinfo.value)
        assert "abc" in str(excinfo.value)
        _clear_env(["TEST_INT"])

    def test_valid_int_respects_limits(self, monkeypatch):
        monkeypatch.setenv("TEST_INT", "5")
        assert parsers.parse_int_env("TEST_INT", default=1, min_val=1, max_val=10) == 5
        _clear_env(["TEST_INT"])

    def test_int_below_min_raises(self, monkeypatch):
        monkeypatch.setenv("TEST_INT", "0")
        with pytest.raises(ValueError):
            parsers.parse_int_env("TEST_INT", default=1, min_val=1)
        _clear_env(["TEST_INT"])

    def test_int_above_max_raises(self, monkeypatch):
        monkeypatch.setenv("TEST_INT", "11")
        with pytest.raises(ValueError):
            parsers.parse_int_env("TEST_INT", default=1, max_val=10)
        _clear_env(["TEST_INT"])


class TestParseFloatEnv:
    def test_invalid_float_raises(self, monkeypatch):
        monkeypatch.setenv("TEST_FLOAT", "abc")
        with pytest.raises(ValueError) as excinfo:
            parsers.parse_float_env("TEST_FLOAT", default=1.0)
        assert "[CONFIG ERROR]" in str(excinfo.value)
        _clear_env(["TEST_FLOAT"])

    def test_valid_float(self, monkeypatch):
        monkeypatch.setenv("TEST_FLOAT", "2.5")
        assert parsers.parse_float_env("TEST_FLOAT", default=1.0, min_val=1.0, max_val=3.0) == 2.5
        _clear_env(["TEST_FLOAT"])


class TestParseBoolEnv:
    def test_invalid_bool_raises(self, monkeypatch):
        monkeypatch.setenv("TEST_BOOL", "maybe")
        with pytest.raises(ValueError) as excinfo:
            parsers.parse_bool_env("TEST_BOOL", default=True)
        assert "[CONFIG ERROR]" in str(excinfo.value)
        _clear_env(["TEST_BOOL"])

    def test_truthy_values(self, monkeypatch):
        for val in ["1", "true", "yes", "on", "Y"]:
            monkeypatch.setenv("TEST_BOOL", val)
            assert parsers.parse_bool_env("TEST_BOOL", default=False) is True
        _clear_env(["TEST_BOOL"])

    def test_falsey_values(self, monkeypatch):
        for val in ["0", "false", "no", "off", "N"]:
            monkeypatch.setenv("TEST_BOOL", val)
            assert parsers.parse_bool_env("TEST_BOOL", default=True) is False
        _clear_env(["TEST_BOOL"])


class TestRemovedParseCsvEnv:
    """parse_csv_env was removed from parsers in this PR."""

    def test_parse_csv_env_does_not_exist(self):
        assert not hasattr(parsers, "parse_csv_env"), (
            "parse_csv_env was removed in this PR and must not be present in core.config.parsers"
        )