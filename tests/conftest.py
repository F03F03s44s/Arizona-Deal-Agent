"""Shared fixtures for Arizona Deal Agent tests."""

import pytest

from app.transmit import reset_stores, set_http_client


@pytest.fixture(autouse=True)
def clean_transmission_state():
    reset_stores()
    set_http_client(None)
    yield
    reset_stores()
    set_http_client(None)
