-- Endpoints/paths table
CREATE TABLE paths
(
    id INTEGER PRIMARY KEY, -- AUTOINCREMENTed
    path TEXT NOT NULL,
    UNIQUE(path)
);

CREATE TABLE parameters
(
    id INTEGER PRIMARY KEY, -- AUTOINCREMENTed
    name VARCHAR NOT NULL,
    method VARCHAR NOT NULL,
    path_id INTEGER NOT NULL,
    FOREIGN KEY(path_id) REFERENCES paths(id),
    UNIQUE(name, method, path_id)
);


CREATE TABLE pvalues
(
    param_id INTEGER,
    value VARCHAR,
    PRIMARY KEY(param_id, value),
    FOREIGN KEY(param_id) REFERENCES parameters(id)
);

CREATE TABLE responses
(
    path_id INTEGER NOT NULL,
    method VARCHAR NOT NULL,
    status VARCHAR(3) NOT NULL,
    content_type VARCHAR NOT NULL,
    PRIMARY KEY(status, path_id, method, content_type),
    FOREIGN KEY(path_id) REFERENCES paths(id)
);
