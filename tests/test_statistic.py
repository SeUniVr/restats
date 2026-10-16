import json
import pytest

import utils.dbmanager as dbm
import core.statistic as stat


@pytest.fixture(autouse=True)
def db(tmp_db):
    dbm.create_connection(tmp_db)
    dbm.createTables()
    yield
    try:
        dbm.closeAndCommit()
    except Exception:
        pass


@pytest.fixture(autouse=True)
def reset_dest(tmp_reports):
    stat.dest = tmp_reports
    yield
    stat.dest = None


# ---------------------------------------------------------------------------
# computeTCL
# ---------------------------------------------------------------------------

def _cov(rate):
    total = 10
    tested = int(total * rate)
    return {"raw": {"documented": total, "documentedAndTested": tested, "totalTested": tested}, "rate": rate}


class TestComputeTCL:

    def test_tcl_0_when_path_coverage_below_1(self):
        d = {k: _cov(0.5) for k in [
            "pathCoverage", "operationCoverage", "statusCoverage",
            "statusClassCoverage", "responseTypeCoverage", "requestTypeCoverage",
            "parameterCoverage", "parameterValueCoverage",
        ]}
        assert stat.computeTCL(d) == 0

    def test_tcl_1_when_only_path_coverage_full(self):
        d = {k: _cov(0.0) for k in [
            "pathCoverage", "operationCoverage", "statusCoverage",
            "statusClassCoverage", "responseTypeCoverage", "requestTypeCoverage",
            "parameterCoverage", "parameterValueCoverage",
        ]}
        d["pathCoverage"] = _cov(1.0)
        assert stat.computeTCL(d) == 1

    def test_tcl_2_when_path_and_operation_full(self):
        d = {k: _cov(0.0) for k in [
            "pathCoverage", "operationCoverage", "statusCoverage",
            "statusClassCoverage", "responseTypeCoverage", "requestTypeCoverage",
            "parameterCoverage", "parameterValueCoverage",
        ]}
        d["pathCoverage"] = _cov(1.0)
        d["operationCoverage"] = _cov(1.0)
        assert stat.computeTCL(d) == 2

    def test_tcl_3_requires_both_content_type_coverages(self):
        d = {k: _cov(0.0) for k in [
            "pathCoverage", "operationCoverage", "statusCoverage",
            "statusClassCoverage", "responseTypeCoverage", "requestTypeCoverage",
            "parameterCoverage", "parameterValueCoverage",
        ]}
        d["pathCoverage"] = _cov(1.0)
        d["operationCoverage"] = _cov(1.0)
        d["responseTypeCoverage"] = _cov(1.0)
        # requestTypeCoverage still 0 — should not reach TCL 3
        assert stat.computeTCL(d) == 2

    def test_tcl_6_when_all_full(self):
        d = {k: _cov(1.0) for k in [
            "pathCoverage", "operationCoverage", "statusCoverage",
            "statusClassCoverage", "responseTypeCoverage", "requestTypeCoverage",
            "parameterCoverage", "parameterValueCoverage",
        ]}
        assert stat.computeTCL(d) == 6


# ---------------------------------------------------------------------------
# Coverage functions — minimal DB population
# ---------------------------------------------------------------------------

SPEC = {
    "/pet": {
        "get": {
            "parameters": {},
            "pathParameters": [],
            "responses": ["200", "404"],
            "produces": ["application/json"],
            "consumes": [],
        },
        "post": {
            "parameters": {"Content-Type": []},
            "pathParameters": [],
            "responses": ["200", "400"],
            "produces": ["application/json"],
            "consumes": ["application/json"],
        },
    }
}


@pytest.fixture
def populated_db(tmp_db):
    """DB with one tested path, one GET and one POST operation."""
    dbm.close()
    dbm.create_connection(tmp_db)
    dbm.createTables()

    path_id = dbm.getPathID("/pet")

    # GET /pet — Accept header, 200 response
    param_id = dbm.getParameterID(path_id, "get", "Accept")
    dbm.addParameterValue(param_id, "application/json")
    dbm.addResponse(path_id, "get", "200", "application/json")

    # POST /pet — Content-Type header, 200 response
    param_id = dbm.getParameterID(path_id, "post", "Content-Type")
    dbm.addParameterValue(param_id, "application/json")
    dbm.addResponse(path_id, "post", "200", "application/json")

    dbm.conn.commit()
    yield tmp_db
    try:
        dbm.closeAndCommit()
    except Exception:
        pass


class TestGetPathCoverage:

    def test_tested_count(self, populated_db):
        result = stat.getPathCoverage(["/pet", "/other"], populated_db)
        assert result["documentedAndTested"] == 1

    def test_total_count(self, populated_db):
        result = stat.getPathCoverage(["/pet", "/other"], populated_db)
        assert result["documented"] == 2

    def test_report_file_written(self, populated_db, tmp_reports):
        stat.getPathCoverage(["/pet"], populated_db)
        report = json.loads((pytest.importorskip("pathlib").Path(tmp_reports) / "path_coverage.json").read_text())
        assert "documentedAndTested" in report
        assert "documentedAndNotTested" in report

    def test_untested_paths_listed(self, populated_db, tmp_reports):
        stat.getPathCoverage(["/pet", "/other"], populated_db)
        from pathlib import Path
        report = json.loads((Path(tmp_reports) / "path_coverage.json").read_text())
        assert "/other" in report["documentedAndNotTested"]


class TestGetOperationCoverage:

    def test_tested_count(self, populated_db):
        result = stat.getOperationCoverage(SPEC, populated_db)
        assert result["documentedAndTested"] == 2

    def test_total_count(self, populated_db):
        result = stat.getOperationCoverage(SPEC, populated_db)
        assert result["documented"] == 2

    def test_report_file_written(self, populated_db, tmp_reports):
        stat.getOperationCoverage(SPEC, populated_db)
        from pathlib import Path
        report = json.loads((Path(tmp_reports) / "operation_coverage.json").read_text())
        assert "documentedAndTested" in report


class TestGetStatusCoverage:

    def test_tested_count(self, populated_db):
        result = stat.getStatusCoverage(SPEC, populated_db)
        assert result["documentedAndTested"] == 2  # 200 for GET and 200 for POST

    def test_total_count(self, populated_db):
        result = stat.getStatusCoverage(SPEC, populated_db)
        assert result["documented"] == 4  # 200+404 for GET, 200+400 for POST


class TestGenerateStats:

    def test_stats_json_written(self, populated_db, tmp_reports):
        conf = {"reportsDir": tmp_reports, "dbPath": populated_db}
        stat.generateStats(SPEC, conf)
        from pathlib import Path
        stats = json.loads((Path(tmp_reports) / "stats.json").read_text())
        assert "pathCoverage" in stats
        assert "operationCoverage" in stats
        assert "TCL" in stats

    def test_stats_rates_are_floats_or_none(self, populated_db, tmp_reports):
        conf = {"reportsDir": tmp_reports, "dbPath": populated_db}
        stat.generateStats(SPEC, conf)
        from pathlib import Path
        stats = json.loads((Path(tmp_reports) / "stats.json").read_text())
        for key in ("pathCoverage", "operationCoverage", "statusCoverage"):
            rate = stats[key]["rate"]
            assert rate is None or isinstance(rate, float)
