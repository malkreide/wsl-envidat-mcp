# Beitragen / Contributing

> 🇩🇪 [Deutsch](#deutsch) · 🇬🇧 [English](#english)

---

## Deutsch

Vielen Dank für Ihr Interesse an diesem Projekt! Beiträge sind willkommen.

### Wie kann ich beitragen?

**Fehler melden:** Erstellen Sie ein [Issue](../../issues) mit einer klaren Beschreibung des Problems, Schritten zur Reproduktion und der erwarteten vs. tatsächlichen Ausgabe.

**Feature vorschlagen:** Beschreiben Sie den Use Case, idealerweise mit einem Bezug zum Schweizer Umweltforschungs-Kontext (Lawinengefahr, Waldzustand, Naturgefahren, Biodiversität etc.).

**Code beitragen:**

1. Forken Sie das Repository
2. Erstellen Sie einen Feature-Branch: `git checkout -b feature/mein-feature`
3. Installieren Sie die Dev-Abhängigkeiten: `pip install -e ".[dev]"`
4. Schreiben Sie Tests für Ihre Änderungen
5. Lint prüfen: `ruff check src/ tests/`
6. Commit mit aussagekräftiger Nachricht (Conventional Commits): `git commit -m "feat: neues Tool für Schneedaten hinzufügen"`
7. Pull Request erstellen

### Code-Standards

- Python 3.11+, Ruff für Linting
- Docstrings auf Englisch (für internationale Kompatibilität)
- Kommentare und Fehlermeldungen dürfen Deutsch oder Englisch sein
- Alle MCP-Tools müssen `readOnlyHint: True` setzen (nur lesender Zugriff)
- Pydantic-Modelle für alle Tool-Inputs
- Nur öffentliche Open-Data-Quellen (OGD) — keine privaten oder lizenzierten APIs

### Tests

Dieses Projekt nutzt Live-API-Integrationstests gegen die öffentliche EnviDat API. Da kein API-Key erforderlich ist, können alle Tests direkt ausgeführt werden:

```bash
# Unit-Tests (kein Netzwerkzugriff)
PYTHONPATH=src pytest tests/ -m "not live"

# Integrationstests (Live-API)
PYTHONPATH=src pytest tests/ -m "live"

# Alle Tests
PYTHONPATH=src pytest tests/
```

### Commit-Nachrichten (Conventional Commits)

| Präfix | Wann verwenden |
|--------|----------------|
| `feat:` | Neues Tool, neue Resource, neue Funktionalität |
| `fix:` | Fehlerbehebung |
| `docs:` | Nur Dokumentationsänderungen |
| `refactor:` | Code-Umstrukturierung ohne Verhaltensänderung |
| `test:` | Neue oder angepasste Tests |
| `chore:` | Build, CI, Abhängigkeiten |

---

## English

Thank you for your interest in this project! Contributions are welcome.

### How can I contribute?

**Report bugs:** Create an [Issue](../../issues) with a clear description, reproduction steps, and expected vs. actual output.

**Suggest features:** Describe the use case, ideally with a reference to Swiss environmental research context (avalanche risk, forest condition, natural hazards, biodiversity, etc.).

**Contribute code:**

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Install dev dependencies: `pip install -e ".[dev]"`
4. Write tests for your changes
5. Run linter: `ruff check src/ tests/`
6. Commit with clear message (Conventional Commits): `git commit -m "feat: add new tool for snow data"`
7. Create a Pull Request

### Code Standards

- Python 3.11+, Ruff for linting
- Docstrings in English (for international compatibility)
- Comments and error messages may be in German or English
- All MCP tools must set `readOnlyHint: True` (read-only access)
- Pydantic models for all tool inputs
- Only public open data sources (OGD) — no private or licensed APIs

### Tests

This project uses live API integration tests against the public EnviDat API. Since no API key is required, all tests can be run directly:

```bash
# Unit tests (no network access)
PYTHONPATH=src pytest tests/ -m "not live"

# Integration tests (live API)
PYTHONPATH=src pytest tests/ -m "live"

# All tests
PYTHONPATH=src pytest tests/
```

### Commit Messages (Conventional Commits)

| Prefix | When to use |
|--------|-------------|
| `feat:` | New tool, new resource, new functionality |
| `fix:` | Bug fix |
| `docs:` | Documentation changes only |
| `refactor:` | Code restructuring without behaviour change |
| `test:` | New or updated tests |
| `chore:` | Build, CI, dependencies |

---

## Lizenz / License

MIT – see [LICENSE](LICENSE)
