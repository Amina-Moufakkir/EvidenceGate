from __future__ import annotations

import os

import pytest


@pytest.mark.skipif(
    not os.environ.get("OPENAI_API_KEY") or os.environ.get("EVIDENCEGATE_LIVE_MODEL_TESTS") != "1",
    reason="live model tests are explicit opt-in",
)
def test_live_model_tests_require_explicit_model() -> None:
    assert os.environ.get("EVIDENCEGATE_MODEL"), "set EVIDENCEGATE_MODEL for live tests"
