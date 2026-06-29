"""transform/key_builder.py のユニットテスト。"""
import pytest
from transform.key_builder import (
    build_race_key, build_entry_key,
    validate_race_key, validate_entry_key,
    race_key_to_parts,
)


def test_build_race_key_basic():
    key = build_race_key(2026, "0330", "05", "01", "01", "01")
    assert key == "2026033005010101"
    assert len(key) == 16


def test_build_race_key_padding():
    key = build_race_key(2026, "0330", 5, 1, 1, 1)
    assert key == "2026033005010101"


def test_build_entry_key():
    race_key = "2026033005010101"
    entry_key = build_entry_key(race_key, 3)
    assert entry_key == "202603300501010103"
    assert len(entry_key) == 18


def test_build_entry_key_padding():
    """馬番が1桁でも2桁ゼロパディングされる。"""
    entry_key = build_entry_key("2026033005010101", 1)
    assert entry_key == "202603300501010101"
    assert len(entry_key) == 18


def test_validate_race_key():
    assert validate_race_key("2026033005010101")
    assert not validate_race_key("2026033005010")
    assert not validate_race_key("abcdefghijklmnop")


def test_validate_entry_key():
    assert validate_entry_key("202603300501010103")
    assert not validate_entry_key("2026033005010101")  # 16桁 = race_key


def test_race_key_to_parts():
    parts = race_key_to_parts("2026033005010101")
    assert parts["kai_nen"] == "2026"
    assert parts["kai_tsuki_hi"] == "0330"
    assert parts["keibajo"] == "05"
    assert parts["kai"] == "01"
    assert parts["nichi_me"] == "01"
    assert parts["race_no"] == "01"
