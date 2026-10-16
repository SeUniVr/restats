import pytest
import utils.dbmanager as dbm


@pytest.fixture(autouse=True)
def db(tmp_db):
    dbm.create_connection(tmp_db)
    dbm.createTables()
    yield
    try:
        dbm.closeAndCommit()
    except Exception:
        pass


class TestConnection:

    def test_tables_created(self):
        # If tables don't exist, any query would raise; getPathCount returns 0 cleanly.
        assert dbm.getPathCount() == 0


class TestPaths:

    def test_get_path_id_creates_new_path(self):
        pid = dbm.getPathID("/pets")
        assert isinstance(pid, int)

    def test_get_path_id_idempotent(self):
        pid1 = dbm.getPathID("/pets")
        pid2 = dbm.getPathID("/pets")
        assert pid1 == pid2

    def test_different_paths_get_different_ids(self):
        pid1 = dbm.getPathID("/pets")
        pid2 = dbm.getPathID("/users")
        assert pid1 != pid2

    def test_get_path_count(self):
        dbm.getPathID("/a")
        dbm.getPathID("/b")
        assert dbm.getPathCount() == 2

    def test_get_path_names(self):
        dbm.getPathID("/pets")
        dbm.getPathID("/users")
        names = dbm.getPathNames()
        assert "/pets" in names
        assert "/users" in names

    def test_get_path_id_by_name_returns_none_for_missing(self):
        assert dbm.getPathIDByName("/nonexistent") is None

    def test_get_path_id_by_name_returns_id_for_existing(self):
        pid = dbm.getPathID("/pets")
        assert dbm.getPathIDByName("/pets") == pid


class TestParameters:

    def test_get_parameter_id_creates_new(self):
        pid = dbm.getPathID("/pets")
        param_id = dbm.getParameterID(pid, "get", "status")
        assert isinstance(param_id, int)

    def test_get_parameter_id_idempotent(self):
        pid = dbm.getPathID("/pets")
        param_id1 = dbm.getParameterID(pid, "get", "status")
        param_id2 = dbm.getParameterID(pid, "get", "status")
        assert param_id1 == param_id2

    def test_same_name_different_method_different_id(self):
        pid = dbm.getPathID("/pets")
        id_get = dbm.getParameterID(pid, "get", "Accept")
        id_post = dbm.getParameterID(pid, "post", "Accept")
        assert id_get != id_post

    def test_method_stored_lowercase(self):
        pid = dbm.getPathID("/pets")
        id1 = dbm.getParameterID(pid, "GET", "Accept")
        id2 = dbm.getParameterID(pid, "get", "Accept")
        assert id1 == id2

    def test_get_parameters_returns_inserted(self):
        pid = dbm.getPathID("/pets")
        dbm.getParameterID(pid, "get", "status")
        rows = dbm.getParameters()
        assert any(path == "/pets" and method == "get" and name == "status"
                   for path, method, name in rows)

    def test_get_parameters_count(self):
        pid = dbm.getPathID("/pets")
        dbm.getParameterID(pid, "get", "Accept")
        dbm.getParameterID(pid, "get", "Host")
        assert dbm.getParametersCount() == 2


class TestParameterValues:

    def test_add_and_retrieve_parameter_value(self):
        pid = dbm.getPathID("/pets")
        param_id = dbm.getParameterID(pid, "get", "status")
        dbm.addParameterValue(param_id, "available")
        values = dbm.getParameterValues(pid, "get", "status")
        assert "available" in values

    def test_multiple_values_for_same_parameter(self):
        pid = dbm.getPathID("/pets")
        param_id = dbm.getParameterID(pid, "get", "status")
        dbm.addParameterValue(param_id, "available")
        dbm.addParameterValue(param_id, "sold")
        values = dbm.getParameterValues(pid, "get", "status")
        assert "available" in values
        assert "sold" in values

    def test_duplicate_parameter_value_ignored(self):
        pid = dbm.getPathID("/pets")
        param_id = dbm.getParameterID(pid, "get", "status")
        dbm.addParameterValue(param_id, "available")
        dbm.addParameterValue(param_id, "available")
        values = dbm.getParameterValues(pid, "get", "status")
        assert values.count("available") == 1

    def test_get_parameter_values_returns_empty_for_unknown_path(self):
        values = dbm.getParameterValues(9999, "get", "status")
        assert values == []


class TestResponses:

    def test_add_response(self):
        pid = dbm.getPathID("/pets")
        dbm.addResponse(pid, "get", "200", "application/json")
        rows = dbm.getStatusCodes()
        assert any(path == "/pets" and method == "get" and status == "200"
                   for path, method, status in rows)

    def test_duplicate_response_ignored(self):
        pid = dbm.getPathID("/pets")
        dbm.addResponse(pid, "get", "200", "application/json")
        dbm.addResponse(pid, "get", "200", "application/json")
        rows = dbm.getStatusCodes()
        matching = [(p, m, s) for p, m, s in rows
                    if p == "/pets" and m == "get" and s == "200"]
        assert len(matching) == 1

    def test_get_status_count(self):
        pid = dbm.getPathID("/pets")
        dbm.addResponse(pid, "get", "200", "application/json")
        dbm.addResponse(pid, "post", "201", "application/json")
        assert dbm.getStatusCount() == 2

    def test_get_response_types(self):
        pid = dbm.getPathID("/pets")
        dbm.addResponse(pid, "get", "200", "application/json")
        rows = dbm.getResponseTypes()
        assert any(path == "/pets" and method == "get" and ct == "application/json"
                   for path, method, ct in rows)

    def test_get_operation_names(self):
        pid = dbm.getPathID("/pets")
        dbm.getParameterID(pid, "get", "Accept")
        dbm.getParameterID(pid, "post", "Content-Type")
        ops = dbm.getOperationNames()
        assert ("get", "/pets") in ops
        assert ("post", "/pets") in ops

    def test_get_operation_count(self):
        pid = dbm.getPathID("/pets")
        dbm.getParameterID(pid, "get", "Accept")
        dbm.getParameterID(pid, "post", "Content-Type")
        assert dbm.getOperationCount() == 2
