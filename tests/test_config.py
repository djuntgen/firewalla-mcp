import pytest

from firewalla_mcp.config import get_msp_domain, get_token


def test_get_token_success(monkeypatch):
    monkeypatch.setenv("FIREWALLA_TOKEN", "secret-token")

    assert get_token() == "secret-token"


def test_get_token_raises_when_unset(monkeypatch):
    monkeypatch.delenv("FIREWALLA_TOKEN", raising=False)

    with pytest.raises(RuntimeError, match="FIREWALLA_TOKEN"):
        get_token()


def test_get_token_raises_on_empty_string(monkeypatch):
    monkeypatch.setenv("FIREWALLA_TOKEN", "")

    with pytest.raises(RuntimeError, match="FIREWALLA_TOKEN"):
        get_token()


def test_get_msp_domain_success(monkeypatch):
    monkeypatch.setenv("FIREWALLA_MSP_DOMAIN", "example.firewalla.net")

    assert get_msp_domain() == "example.firewalla.net"


def test_get_msp_domain_raises_when_unset(monkeypatch):
    monkeypatch.delenv("FIREWALLA_MSP_DOMAIN", raising=False)

    with pytest.raises(RuntimeError, match="FIREWALLA_MSP_DOMAIN"):
        get_msp_domain()
