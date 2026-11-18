"""Pins that the gate Hypothesis profile is in force; this module does not import the helper itself.

tests/conftest.py and the property modules both import hypothesis_gate, so this catches a regression of the
profile's settings, or of the loading only if conftest and every property module stop loading it together.
"""

import pytest

pytest.importorskip("hypothesis", reason="hypothesis is a dev-only dependency (requirements-dev.txt)")

from hypothesis import Phase, settings  # noqa: E402


def test_gate_profile_is_loaded():
    assert settings.get_current_profile_name() == "gate"
    assert settings().derandomize is True
    assert settings().database is None
    assert settings().deadline is None
    assert Phase.shrink not in settings().phases
