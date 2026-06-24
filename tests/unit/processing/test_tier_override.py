"""Tests for tier override CRUD (T059)."""

from __future__ import annotations

import pytest
from src.processing.classifier import Classifier


def test_override_changes_tier() -> None:
    classifier = Classifier(overrides={"open browser": "complex"})
    assert classifier.classify("open browser") == "complex"


def test_override_case_insensitive() -> None:
    classifier = Classifier(overrides={"Open Browser": "complex"})
    assert classifier.classify("Open Browser") == "complex"


def test_override_takes_priority_over_keyword() -> None:
    # "open" is normally simple; override forces complex
    classifier = Classifier(overrides={"open the terminal": "complex"})
    assert classifier.classify("open the terminal") == "complex"


def test_no_override_uses_keyword_classification() -> None:
    classifier = Classifier(overrides={})
    assert classifier.classify("open browser") == "simple"


def test_unknown_prompt_defaults_to_complex() -> None:
    classifier = Classifier(overrides={})
    assert classifier.classify("xyzzy frobnicate") == "complex"
