# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with this repository.

## Running tests

```bash
pip install -r requirements-dev.txt
python3 -m pytest tests/ -v          # all tests
python3 -m pytest tests/test_parsers.py -v  # single file
```

Tests must be run from the project root (not from inside `tests/`) because `dbmanager.createTables()` opens `./utils/create_tables.sql` relative to the working directory. The `conftest.py` `autouse` fixture enforces this automatically.

## Running Restats

```bash
python app.py                    # uses config.json by default
python app.py /path/to/config.json  # explicit config path
```

`app.py` must be run from the project root because `utils/dbmanager.py` opens `./utils/create_tables.sql` with a relative path.

## Configuration

Copy `config_template.json` to `config.json` and fill in absolute paths:

- `modules`: `"dataCollection"` | `"statistics"` | `"all"`
- `specification`: absolute path to an OpenAPI/Swagger JSON spec
- `dumpsDir`: directory of WebScarab-format HTTP dump files
- `reportsDir`: directory where JSON reports will be written
- `dbPath`: path to the SQLite database file (created if absent)

## Architecture

The tool has two sequential pipeline stages, each corresponding to a `modules` value:

### Stage 1 — `dataCollection` (`core/pairing.py`)

Reads HTTP dump files from `dumpsDir`. Dump files come in numbered pairs: `N-request.txt` and `N-response.txt` (WebScarab plain-text format captured via Burp proxy + Burp dump extension).

For each pair:
1. `utils/parsers.py` parses raw HTTP request/response files into dicts.
2. The request path is matched against spec paths using compiled regexes; path parameters like `{id}` become `[^/]+`.
3. Matched pairs are stored in a SQLite database (`utils/dbmanager.py`) with four tables: `paths`, `parameters`, `pvalues`, `responses`.

Unmatched requests (paths not in the spec) are silently skipped.

### Stage 2 — `statistics` (`core/statistic.py`)

Reads the database and the parsed spec to compute eight coverage metrics, writing one JSON report file per metric to `reportsDir`, plus a summary `stats.json`:

| Metric | Report file |
|--------|-------------|
| Path coverage | `path_coverage.json` |
| Operation (method) coverage | `operation_coverage.json` |
| Status code coverage | `status_coverage.json` |
| Status class (1xx/2xx…) coverage | `status_class_coverage.json` |
| Response content-type coverage | `response_type_coverage.json` |
| Request content-type coverage | `request_type_coverage.json` |
| Parameter coverage | `parameter_coverage.json` |
| Parameter value coverage | `parameter_value_coverage.json` |

Each report distinguishes `documentedAndTested`, `documentedAndNotTested`, and `notDocumentedAndTested` entries. The overall `stats.json` includes a **Test Coverage Level (TCL)** (0–6) computed hierarchically: each level requires 100% coverage of all metrics at lower levels.

### Spec parsing (`utils/parsers.py`)

`extractSpecificationData()` detects Swagger 2 vs. OpenAPI 3 and normalises both into an internal dict keyed by path → method → `{parameters, responses, produces, consumes}`. Parameter enum/boolean values are preserved for parameter-value coverage.

## Known issues / TODOs in the code

- `getStatusCount()` and `getResponseTypesCount()` in `dbmanager.py` are documented as counting more than expected (includes undocumented status codes).
- `getStatusClassCoverage()` in `statistic.py` has an indentation bug: the set-to-list casting and file write are inside the outer `for path` loop instead of after it, so `status_class_coverage.json` may be written with incomplete data.
- `statistic.py:dest` is a module-level global; `generateStats()` must be called before any coverage function or `dest` will be `None`.
