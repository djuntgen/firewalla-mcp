from importlib.metadata import version

import firewalla_mcp


def test_dunder_version_matches_package_metadata():
    assert firewalla_mcp.__version__ == version("firewalla-mcp")
