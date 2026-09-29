import pytest


@pytest.fixture
def ctx():
    """Shared state between Gherkin steps."""
    return {}
