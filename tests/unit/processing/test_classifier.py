"""Tests for three-tier classifier (US2). Write first — confirm FAIL before implementing."""

import pytest
from unittest.mock import patch, MagicMock


def make_classifier() -> object:
    from src.processing.classifier import Classifier
    return Classifier(overrides={})


def test_simple_tier_for_open_browser() -> None:
    clf = make_classifier()
    assert clf.classify("open my browser") == "simple"


def test_simple_tier_for_what_time() -> None:
    clf = make_classifier()
    assert clf.classify("what time is it") == "simple"


def test_medium_tier_for_create_file() -> None:
    clf = make_classifier()
    assert clf.classify("create a new file called notes.txt") == "medium"


def test_medium_tier_for_install_package() -> None:
    clf = make_classifier()
    assert clf.classify("install the requests package") == "medium"


def test_complex_tier_for_delete() -> None:
    clf = make_classifier()
    assert clf.classify("delete the old log files") == "complex"


def test_complex_tier_for_commit() -> None:
    clf = make_classifier()
    assert clf.classify("commit my changes with the message fix bug") == "complex"


def test_complex_tier_for_write_code() -> None:
    clf = make_classifier()
    assert clf.classify("write a Python function to parse CSV files") == "complex"


def test_tier_override_takes_precedence() -> None:
    from src.processing.classifier import Classifier
    clf = Classifier(overrides={"delete": "simple"})
    assert clf.classify("delete the temp folder") == "simple"


def test_unknown_defaults_to_complex() -> None:
    clf = make_classifier()
    result = clf.classify("xyzzy frobnicate the quantum widget")
    assert result == "complex"
