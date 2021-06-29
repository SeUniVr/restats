# Restats

Test coverage computation tool for REST API test suites.

---

## About
Restats computes test coverage metrics, statistics and the test coverage level (TCL) for test suites excercising REST APIs. Metrics, statistics, and the TCL are computed from the interface perspective, i.e., considering the completeness of the test suite with respect to the elements defined in the specification.

Restats inputs are:
- the OpenAPI specification of the REST API under test;
- the HTTP log of requests and resonses occuring at testing time.

---

## Recording HTTP requests and responses
To record HTTP requests and resposes occuring at testing time, we suggest to use the Burp proxy and the Burp dump extension. HTTP dumps must be in the WebScarab plain-text format. Some examples of requests and reponses are available in the `example/dumps` folder of this repository.

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
- `statistics`: reads data in the database to comupte metrics, statistics, and the TCL;
- `all`: both the aforementioned modules.

Set the `specification` field with the absolute path of the OpenAPI specification of the API under test.

Set the `dumpsDir` field with the absolute path of the directory containing the dump of requests and responses occurred at testing time.

Set the `reportsDir` field with the absolute path of the directory in which you want the reports to be written.

Set the `dbPath` field with the absolute path of the SQLite database file. If the database file does not exist, Restats will create it.

---

## Launch

To launch Restats, just run `app.py` with python (e.g., `python app.py`).