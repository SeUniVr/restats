from pathlib import Path
import pytest

import utils.parsers as parsers

PROJECT_ROOT = Path(__file__).parent.parent
DUMPS = PROJECT_ROOT / "example" / "dumps"


class TestRawHTTPRequest2Dict:

    def test_get_request_method_and_path(self):
        result = parsers.RawHTTPRequest2Dict(DUMPS / "1-request.txt")
        assert result["method"] == "get"
        assert result["path"] == "/v2/pet"

    def test_get_request_no_body(self):
        result = parsers.RawHTTPRequest2Dict(DUMPS / "1-request.txt")
        assert result["body"] == {}

    def test_get_request_burp_header_stripped(self):
        result = parsers.RawHTTPRequest2Dict(DUMPS / "1-request.txt")
        header_names = [p["name"] for p in result["parameters"]]
        assert "X-Burp-Comment" not in header_names

    def test_get_request_standard_headers_present(self):
        result = parsers.RawHTTPRequest2Dict(DUMPS / "1-request.txt")
        header_names = [p["name"] for p in result["parameters"]]
        assert "Accept" in header_names
        assert "Host" in header_names

    def test_post_request_json_body_parsed(self):
        result = parsers.RawHTTPRequest2Dict(DUMPS / "2-request.txt")
        assert result["method"] == "post"
        assert "name" in result["body"]
        assert result["body"]["name"] == "doggie"
        assert "photoUrls" in result["body"]

    def test_post_request_content_type_header(self):
        result = parsers.RawHTTPRequest2Dict(DUMPS / "2-request.txt")
        header_names = [p["name"] for p in result["parameters"]]
        assert "Content-Type" in header_names

    def test_url_and_version_captured(self):
        result = parsers.RawHTTPRequest2Dict(DUMPS / "1-request.txt")
        assert result["version"] == "HTTP/1.1"
        assert "/v2/pet" in result["url"]


class TestRawHTTPResponse2Dict:

    def test_200_status(self):
        result = parsers.RawHTTPResponse2Dict(DUMPS / "1-response.txt")
        assert result["status"] == "200"

    def test_content_type_charset_stripped(self):
        result = parsers.RawHTTPResponse2Dict(DUMPS / "1-response.txt")
        ct_headers = [p for p in result["parameters"] if p["name"] == "Content-Type"]
        assert len(ct_headers) == 1
        assert "charset" not in ct_headers[0]["value"]
        assert ct_headers[0]["value"] == "application/json"

    def test_500_status(self):
        result = parsers.RawHTTPResponse2Dict(DUMPS / "2-response.txt")
        assert result["status"] == "500"

    def test_405_status(self):
        result = parsers.RawHTTPResponse2Dict(DUMPS / "5-response.txt")
        assert result["status"] == "405"

    def test_burp_header_stripped(self):
        result = parsers.RawHTTPResponse2Dict(DUMPS / "1-response.txt")
        header_names = [p["name"] for p in result["parameters"]]
        assert "X-Burp-Comment" not in header_names

    def test_empty_file_returns_empty_dict(self, tmp_path):
        empty = tmp_path / "empty.txt"
        empty.write_bytes(b"")
        result = parsers.RawHTTPResponse2Dict(empty)
        assert result == {}


class TestExtractSpecificationData:

    def test_swagger2_base_path(self, petstore_spec):
        data = parsers.extractSpecificationData(petstore_spec)
        assert data["bases"] == ["/v2"]

    def test_swagger2_paths_present(self, petstore_spec):
        data = parsers.extractSpecificationData(petstore_spec)
        assert "/pet" in data
        assert "/pet/findByStatus" in data
        assert "/pet/findByTags" in data
        assert "/pet/{petId}" in data

    def test_swagger2_operations_present(self, petstore_spec):
        data = parsers.extractSpecificationData(petstore_spec)
        assert "get" in data["/pet"]
        assert "post" in data["/pet"]
        assert "put" in data["/pet"]

    def test_swagger2_responses_extracted(self, petstore_spec):
        data = parsers.extractSpecificationData(petstore_spec)
        assert "200" in data["/pet"]["get"]["responses"]
        assert "400" in data["/pet"]["get"]["responses"]

    def test_swagger2_produces_extracted(self, petstore_spec):
        data = parsers.extractSpecificationData(petstore_spec)
        assert "application/json" in data["/pet"]["get"]["produces"]

    def test_swagger2_consumes_extracted(self, petstore_spec):
        data = parsers.extractSpecificationData(petstore_spec)
        assert "application/json" in data["/pet"]["post"]["consumes"]

    def test_swagger2_array_items_enum_not_extracted(self, petstore_spec):
        # The petstore status param uses type:array with items.enum; the parser
        # only reads top-level parameter.enum, so the values come back empty.
        data = parsers.extractSpecificationData(petstore_spec)
        status_values = data["/pet/findByStatus"]["get"]["parameters"].get("status", [])
        assert status_values == []

    def test_swagger2_path_parameter_not_in_parameters(self, petstore_spec):
        data = parsers.extractSpecificationData(petstore_spec)
        assert "petId" not in data["/pet/{petId}"]["get"]["parameters"]
        assert "petId" in data["/pet/{petId}"]["get"]["pathParameters"]

    def test_openapi3_base_path(self, openapi3_spec):
        data = parsers.extractSpecificationData(openapi3_spec)
        assert "/api/v1" in data["bases"]

    def test_openapi3_paths_present(self, openapi3_spec):
        data = parsers.extractSpecificationData(openapi3_spec)
        assert "/users" in data
        assert "/users/{id}" in data

    def test_openapi3_response_content_types_extracted(self, openapi3_spec):
        data = parsers.extractSpecificationData(openapi3_spec)
        assert "application/json" in data["/users"]["get"]["produces"]

    def test_openapi3_request_body_consumes_extracted(self, openapi3_spec):
        data = parsers.extractSpecificationData(openapi3_spec)
        assert "application/json" in data["/users"]["post"]["consumes"]

    def test_openapi3_enum_parameter_values_saved(self, openapi3_spec):
        data = parsers.extractSpecificationData(openapi3_spec)
        fmt_values = data["/users/{id}"]["get"]["parameters"].get("format", [])
        assert set(fmt_values) == {"json", "xml"}

    def test_openapi3_path_parameter_excluded_from_parameters(self, openapi3_spec):
        data = parsers.extractSpecificationData(openapi3_spec)
        assert "id" not in data["/users/{id}"]["get"]["parameters"]
        assert "id" in data["/users/{id}"]["get"]["pathParameters"]

    def test_missing_spec_file_exits(self, tmp_path):
        with pytest.raises(SystemExit):
            parsers.extractSpecificationData(str(tmp_path / "nonexistent.json"))
