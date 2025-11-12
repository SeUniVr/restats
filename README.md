# Restats

Test coverage computation tool for REST API test suites.

> **To cite the tool:**<br>
> D. Corradini, A. Zampieri, M. Pasqua and M. Ceccato, *"Restats: A Test Coverage Tool for RESTful APIs"*. IEEE International Conference on Software Maintenance and Evolution (ICSME), Luxembourg, 2021, pp. 594-598. DOI: [10.1109/ICSME52107.2021.00063](https://doi.org/10.1109/ICSME52107.2021.00063).
---

## About
Restats computes test coverage metrics, statistics, and the test coverage level (TCL) for test suites exercising REST APIs. Metrics, statistics, and the TCL are computed from the interface perspective, i.e., considering the completeness of the test suite with respect to the elements defined in the specification.

Restats inputs are:
- the OpenAPI specification of the REST API under test;
- the HTTP log of requests and responses occurring at testing time.

---

## Recording HTTP requests and responses
To record HTTP requests and responses occurring at testing time, we suggest to use the Burp proxy and the Burp dump extension. HTTP dumps must be in the WebScarab plain-text format. Some examples of requests and responses are available in the `example/dumps` folder of this repository.

---

## Configuration
Use the `config.json` file to configure Restats. The structure of the file is the following:

```
{
	"modules": "all | dataCollection | statistics",
	"specification": "/path/to/specification.json",
	"dumpsDir": "/path/to/dumps",
	"reportsDir": "/path/to/reports",
	"dbPath": "/path/to/database.sqlite"
}
```

With `modules` you can set the modules to run:
- `dataCollection`: reads the dumps and fills the database;
- `statistics`: reads data in the database to compute metrics, statistics, and the TCL;
- `all`: both the aforementioned modules.

Set the `specification` field with the absolute path of the OpenAPI specification of the API under test.

Set the `dumpsDir` field with the absolute path of the directory containing the dump of requests and responses that occurred during testing.

Set the `reportsDir` field with the absolute path of the directory in which you want the reports to be written.

Set the `dbPath` field with the absolute path of the SQLite database file. If the database file does not exist, Restats will create it.

---

## Launch

To launch Restats, just run `app.py` with Python (e.g., `python app.py`).
