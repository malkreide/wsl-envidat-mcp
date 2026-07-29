"""
wsl-envidat-mcp
===============
MCP Server for WSL/EnviDat environmental research data.

Data from the Swiss Federal Research Institute for Forest, Snow and Landscape (WSL)
via EnviDat (www.envidat.ch). No API key required.

Domains: Forest · Biodiversity · Natural Hazards · Snow & Ice · Landscape
Part of the Swiss public sector MCP server portfolio.
Model-agnostic: works with Claude, GPT, Ollama, and any MCP-compatible client.
"""

from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _distribution_version

try:
    # Read the version from the installed distribution metadata, which is built
    # from pyproject.toml. Hand-maintaining the literal here let the numbers
    # drift apart: pyproject said 0.2.3, this said 0.1.0. A value nobody
    # has to remember to bump cannot go stale.
    __version__ = _distribution_version("wsl-envidat-mcp")
except PackageNotFoundError:
    # Running from the source tree without an install (e.g. a bare checkout).
    # Deliberately not a plausible-looking number: an obviously non-release
    # marker is better than a wrong version in the User-Agent.
    __version__ = "0.0.0+source"
__author__ = "malkreide"
__license__ = "MIT"

__all__ = ["__version__", "__author__", "__license__"]
