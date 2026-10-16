import os
import pytest
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent


@pytest.fixture(autouse=True)
def project_cwd():
    # dbmanager.createTables() opens './utils/create_tables.sql' relative to cwd
    original = os.getcwd()
    os.chdir(PROJECT_ROOT)
    yield
    os.chdir(original)


@pytest.fixture
def tmp_db(tmp_path):
    return str(tmp_path / "test.sqlite")


@pytest.fixture
def tmp_reports(tmp_path):
    reports = tmp_path / "reports"
    reports.mkdir()
    return str(reports)


@pytest.fixture
def petstore_spec():
    return str(PROJECT_ROOT / "example" / "petstore.json")


@pytest.fixture
def dumps_dir():
    return str(PROJECT_ROOT / "example" / "dumps")


@pytest.fixture
def openapi3_spec(tmp_path):
    import json
    spec = {
        "openapi": "3.0.0",
        "info": {"title": "Test API", "version": "1.0.0"},
        "servers": [{"url": "http://localhost/api/v1"}],
        "paths": {
            "/users": {
                "get": {
                    "responses": {
                        "200": {"description": "OK", "content": {"application/json": {}}},
                        "404": {"description": "Not Found"},
                    }
                },
                "post": {
                    "requestBody": {"content": {"application/json": {}}},
                    "responses": {"201": {"description": "Created"}},
                },
            },
            "/users/{id}": {
                "get": {
                    "parameters": [
                        {"name": "id", "in": "path", "required": True, "schema": {"type": "integer"}},
                        {
                            "name": "format",
                            "in": "query",
                            "schema": {"type": "string", "enum": ["json", "xml"]},
                        },
                    ],
                    "responses": {"200": {"description": "OK"}},
                }
            },
        },
    }
    path = tmp_path / "openapi3.json"
    path.write_text(json.dumps(spec))
    return str(path)
