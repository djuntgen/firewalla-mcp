import pytest

from firewalla_mcp.config import get_msp_domain, get_timeout, get_token


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


def test_get_msp_domain_strips_https_scheme(monkeypatch):
    monkeypatch.setenv("FIREWALLA_MSP_DOMAIN", "https://example.firewalla.net")

    assert get_msp_domain() == "example.firewalla.net"


def test_get_msp_domain_strips_http_scheme_and_trailing_slash(monkeypatch):
    monkeypatch.setenv("FIREWALLA_MSP_DOMAIN", "http://example.firewalla.net/")

    assert get_msp_domain() == "example.firewalla.net"


def test_get_msp_domain_rejects_domain_with_path(monkeypatch):
    monkeypatch.setenv("FIREWALLA_MSP_DOMAIN", "example.firewalla.net/v2")

    with pytest.raises(RuntimeError, match="hostname"):
        get_msp_domain()


def test_get_timeout_defaults_to_10_seconds(monkeypatch):
    monkeypatch.delenv("FIREWALLA_TIMEOUT", raising=False)

    assert get_timeout() == 10.0


def test_get_timeout_reads_env_var(monkeypatch):
    monkeypatch.setenv("FIREWALLA_TIMEOUT", "30")

    assert get_timeout() == 30.0


def test_get_timeout_rejects_non_numeric(monkeypatch):
    monkeypatch.setenv("FIREWALLA_TIMEOUT", "fast")

    with pytest.raises(RuntimeError, match="FIREWALLA_TIMEOUT"):
        get_timeout()
