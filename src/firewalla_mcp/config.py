import os


def get_token() -> str:
    token = os.environ.get("FIREWALLA_TOKEN", "").strip()
    if not token:
        raise RuntimeError(
            "FIREWALLA_TOKEN is not set. Export your Firewalla MSP API personal "
            "access token, e.g. FIREWALLA_TOKEN=$(op read 'op://Vault/Firewalla PAT/password')"
        )
    return token


def get_msp_domain() -> str:
    domain = os.environ.get("FIREWALLA_MSP_DOMAIN", "").strip()
    if not domain:
        raise RuntimeError(
            "FIREWALLA_MSP_DOMAIN is not set. Export your Firewalla MSP domain, "
            "e.g. FIREWALLA_MSP_DOMAIN=your-alias.firewalla.net"
        )
    domain = domain.removeprefix("https://").removeprefix("http://").rstrip("/")
    if "/" in domain:
        raise RuntimeError(
            f"FIREWALLA_MSP_DOMAIN must be a bare hostname like "
            f"your-alias.firewalla.net, got {domain!r}"
        )
    return domain


def get_timeout() -> float:
    raw = os.environ.get("FIREWALLA_TIMEOUT", "").strip()
    if not raw:
        return 10.0
    try:
        return float(raw)
    except ValueError:
        raise RuntimeError(
            f"FIREWALLA_TIMEOUT must be a number of seconds, got {raw!r}"
        ) from None
