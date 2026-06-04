# Contributing to wsl-envidat-mcp

Thank you for your interest in contributing to this project! This MCP server is part of the [Swiss Public Data MCP Portfolio](https://github.com/malkreide) and follows shared conventions across the portfolio.

[🇩🇪 Deutsche Version](CONTRIBUTING.de.md)

---

## Table of Contents

- [Reporting Issues](#reporting-issues)
- [Development Setup](#development-setup)
- [Making Changes](#making-changes)
- [Code Style](#code-style)
- [Testing](#testing)
- [Submitting a Pull Request](#submitting-a-pull-request)
- [Data Sources & Attribution](#data-sources--attribution)

---

## Reporting Issues

Before opening an issue, please check [existing issues](https://github.com/malkreide/wsl-envidat-mcp/issues) to avoid duplicates.

When reporting a bug, please include:

- A clear description of the problem
- Steps to reproduce
- Expected vs. actual behaviour
- Python version and OS
- Relevant error messages or logs

For API-related issues (e.g. endpoint or schema changes at envidat.ch), please note that this server depends on the external EnviDat CKAN API, which may change without notice.

---

## Development Setup

```bash
# 1. Clone the repository
git clone https://github.com/malkreide/wsl-envidat-mcp.git
cd wsl-envidat-mcp

# 2. Install in editable mode with dev dependencies
pip install -e ".[dev]"

# 3. Verify the server starts
python -m wsl_envidat_mcp.server
```

**Requirements:**
- Python 3.11+
- No API keys required – all data sources are publicly accessible

---

## Making Changes

1. **Fork** the repository and create a feature branch:
   ```bash
   git checkout -b feat/your-feature-name
   ```

2. Follow the [Conventional Commits](https://www.conventionalcommits.org/) format:

   | Type | When to use |
   |---|---|
   | `feat` | New tool or capability |
   | `fix` | Bug fix |
   | `docs` | Documentation only |
   | `refactor` | Code restructuring, no behaviour change |
   | `test` | Adding or updating tests |
   | `chore` | Build, dependencies, CI |

3. Update `CHANGELOG.md` under `[Unreleased]` for any user-visible change.

4. If you add a new tool, update both `README.md` and `README.de.md` accordingly.

---

## Code Style

This project uses [Ruff](https://docs.astral.sh/ruff/) for linting and formatting.

```bash
# Check for linting issues
ruff check src/

# Auto-fix where possible
ruff check src/ --fix

# Format code
ruff format src/
```

The CI pipeline runs Ruff on every push – PRs with linting errors will not be merged.

**General conventions:**
- Type hints on all public functions
- Pydantic v2 for input validation at all tool boundaries
- `httpx` for HTTP calls
- All MCP tools must set `readOnlyHint: True` (read-only access only)
- Descriptive tool descriptions (they are read by the AI model)
- Only public open data sources (OGD) — no private or licensed APIs

---

## Testing

```bash
# Unit tests only (offline, no network — CKAN responses mocked via respx)
PYTHONPATH=src pytest tests/ -m "not live"

# Integration tests (live calls to envidat.ch)
PYTHONPATH=src pytest tests/ -m "live"

# Full suite
PYTHONPATH=src pytest tests/
```

Tests are marked with `@pytest.mark.live` when they call external APIs. The CI pipeline runs only non-live tests on PRs to avoid flakiness from external dependencies; the live suite runs on `main` pushes and manual `workflow_dispatch` triggers.

When adding a new tool, please add at least one unit test and one live integration test.

---

## Submitting a Pull Request

1. Ensure all tests pass and Ruff reports no errors
2. Update `CHANGELOG.md`
3. Push your branch and open a pull request against `main`
4. Describe what changed and why – link any related issues

PRs that introduce breaking changes to existing tool signatures require a discussion first.

---

## Data Sources & Attribution

This server uses open data from the WSL via the EnviDat platform:

| Source | Provider | Terms |
|---|---|---|
| [envidat.ch](https://www.envidat.ch/) | WSL / EnviDat (CKAN API) | Open licences (Creative Commons, CC0), per-dataset |

Individual datasets on EnviDat are published under **various open licences** (Creative Commons, CC0) — see each dataset's metadata for the applicable licence and attribution requirements. Any contribution that incorporates additional data sources must document their licence and attribution requirements here.

---

## Portfolio Context

This server is part of a coherent portfolio of Swiss open-data MCP servers. When contributing, please consider:

- **No-Auth-First**: prefer endpoints that require no authentication
- **Read-only**: all tools perform HTTP GET requests only — no data is written, modified, or deleted upstream
- **Graceful degradation**: the server should start and provide partial functionality even if the API is unreachable
- **Bilingual docs**: user-facing documentation changes must be reflected in both `README.md` (English) and `README.de.md` (German)

---

Questions? Open a [GitHub Discussion](https://github.com/malkreide/wsl-envidat-mcp/discussions) or file an issue.
