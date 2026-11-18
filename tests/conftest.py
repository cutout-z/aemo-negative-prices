"""Shared pytest setup."""

try:  # dev-only: load the fixed Hypothesis profile for every run when Hypothesis is installed
    import hypothesis_gate  # noqa: F401
except ModuleNotFoundError as exc:
    if exc.name != "hypothesis":  # a broken helper must fail loudly, not be skipped
        raise
