"""
End-to-end integration tests using the example petstore spec and dumps.

Dumps summary (5 pairs against /v2/pet):
  1: GET  /v2/pet → 200
  2: POST /v2/pet → 500
  3: POST /v2/pet → 200
  4: GET  /v2/pet → 200  (duplicate of pair 1)
  5: PATCH /v2/pet → 405  (PATCH is not in the spec — notDocumentedAndTested)
"""
import json
from pathlib import Path

import pytest
import utils.parsers as parsers
import core.pairing as pairing
import core.statistic as stat
import utils.dbmanager as dbm


@pytest.fixture
def petstore_spec_dict(petstore_spec):
    data = parsers.extractSpecificationData(petstore_spec)
    return data


@pytest.fixture
def populated_db(tmp_db, petstore_spec, dumps_dir):
    spec = parsers.extractSpecificationData(petstore_spec)
    bases = spec.pop("bases")
    paths = list(spec.keys())
    conf = {"dumpsDir": dumps_dir, "dbPath": tmp_db}
    pairing.generatePairs(conf, paths, bases)
    yield tmp_db, spec


class TestDataCollection:

    def test_pet_path_stored(self, populated_db):
        tmp_db, _ = populated_db
        dbm.create_connection(tmp_db)
        names = dbm.getPathNames()
        dbm.close()
        assert "/pet" in names

    def test_get_and_post_operations_stored(self, populated_db):
        tmp_db, _ = populated_db
        dbm.create_connection(tmp_db)
        ops = dbm.getOperationNames()
        dbm.close()
        methods = {m for m, _ in ops}
        assert "get" in methods
        assert "post" in methods

    def test_200_and_500_responses_stored(self, populated_db):
        tmp_db, _ = populated_db
        dbm.create_connection(tmp_db)
        codes = {status for _, _, status in dbm.getStatusCodes()}
        dbm.close()
        assert "200" in codes
        assert "500" in codes

    def test_unmatched_path_not_stored(self, populated_db):
        tmp_db, _ = populated_db
        dbm.create_connection(tmp_db)
        names = dbm.getPathNames()
        dbm.close()
        # Only /pet should be stored; other spec paths were never requested
        for name in names:
            assert name == "/pet"


class TestStatistics:

    def test_path_coverage_rate(self, populated_db, tmp_reports):
        tmp_db, spec = populated_db
        conf = {"reportsDir": tmp_reports, "dbPath": tmp_db}
        stat.generateStats(spec, conf)
        stats = json.loads((Path(tmp_reports) / "stats.json").read_text())
        # 1 out of 4 spec paths covered
        assert stats["pathCoverage"]["raw"]["documentedAndTested"] == 1
        assert stats["pathCoverage"]["raw"]["documented"] == 4

    def test_operation_coverage_get_and_post_tested(self, populated_db, tmp_reports):
        tmp_db, spec = populated_db
        conf = {"reportsDir": tmp_reports, "dbPath": tmp_db}
        stat.generateStats(spec, conf)
        report = json.loads((Path(tmp_reports) / "operation_coverage.json").read_text())
        assert "get" in report["documentedAndTested"].get("/pet", [])
        assert "post" in report["documentedAndTested"].get("/pet", [])

    def test_patch_is_not_documented(self, populated_db, tmp_reports):
        tmp_db, spec = populated_db
        conf = {"reportsDir": tmp_reports, "dbPath": tmp_db}
        stat.generateStats(spec, conf)
        report = json.loads((Path(tmp_reports) / "operation_coverage.json").read_text())
        assert "patch" in report.get("notDocumentedAndTested", {}).get("/pet", [])

    def test_response_content_type_coverage_report_exists(self, populated_db, tmp_reports):
        tmp_db, spec = populated_db
        conf = {"reportsDir": tmp_reports, "dbPath": tmp_db}
        stat.generateStats(spec, conf)
        assert (Path(tmp_reports) / "response_type_coverage.json").exists()

    def test_all_report_files_written(self, populated_db, tmp_reports):
        tmp_db, spec = populated_db
        conf = {"reportsDir": tmp_reports, "dbPath": tmp_db}
        stat.generateStats(spec, conf)
        expected = [
            "stats.json",
            "path_coverage.json",
            "operation_coverage.json",
            "status_coverage.json",
            "response_type_coverage.json",
            "request_type_coverage.json",
            "parameter_coverage.json",
            "parameter_value_coverage.json",
        ]
        for filename in expected:
            assert (Path(tmp_reports) / filename).exists(), f"{filename} not found"

    def test_tcl_is_integer(self, populated_db, tmp_reports):
        tmp_db, spec = populated_db
        conf = {"reportsDir": tmp_reports, "dbPath": tmp_db}
        stat.generateStats(spec, conf)
        stats = json.loads((Path(tmp_reports) / "stats.json").read_text())
        assert isinstance(stats["TCL"], int)
        assert 0 <= stats["TCL"] <= 6
