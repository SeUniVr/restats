import sqlite3
from sqlite3 import Error

conn = None

def create_connection(dbfile):
    """ create a database connection to the SQLite database
        specified by db_file
    :param db_file: database file
    :return: Connection object or None
    """
    global conn

    try:
        conn = sqlite3.connect(dbfile)
        conn.execute('PRAGMA synchronous = OFF')

    except Error as e:
        print(e)
        quit()


def closeAndCommit():
    global conn

    conn.commit()
    conn.close()


def close():
    global conn

    conn.close()


def createTables():

    with open('./utils/create_tables.sql', 'r') as sqlfile:
        sql = sqlfile.read()

    try:
        conn.executescript(sql)

    except Error as e:
        pass

def getPathID(path):
    c = conn.cursor()

    sql = 'SELECT id FROM paths WHERE path = ?'
    c.execute(sql, (path,))
    row = c.fetchone()

    if row == None:
        sql = 'INSERT INTO paths VALUES (NULL, ?)'
        c.execute(sql, (path,))
        conn.commit()
        return getPathID(path)

    return row[0]


def getParameterID(pathID, method, parameter):

    method = method.lower()

    c = conn.cursor()
    sql = 'SELECT id FROM parameters WHERE name = ? AND method = ? AND path_id = ?'
    c.execute(sql, (parameter, method, pathID))
    row = c.fetchone()

    if row == None:
        sql = 'INSERT INTO parameters VALUES (NULL, ?, ?, ?)'
        c.execute(sql, (parameter, method, pathID))
        conn.commit()
        return getParameterID(pathID, method, parameter)

    return row[0]


def addParameterValue(parameterID, value):
    sql = 'INSERT OR IGNORE INTO pvalues VALUES (?, ?)'

    conn.execute(sql, (parameterID, str(value)))


def addResponse(pathID, method, status, cType, responseBody):
    method = method.lower()

    sql = 'INSERT OR IGNORE INTO responses VALUES (?, ?, ?, ?, ?)'

    conn.execute(sql, (pathID, method, status, cType, responseBody))


def getValues():

    sql = 'SELECT * FROM paths'
    c = conn.cursor()
    c.execute(sql)
    for l in c.fetchall():
        print(l)

    sql = 'SELECT * FROM parameters'
    c = conn.cursor()
    c.execute(sql)
    for l in c.fetchall():
        print(l)

    sql = 'SELECT * FROM pvalues'
    c = conn.cursor()
    c.execute(sql)
    for l in c.fetchall():
        print(l)

    sql = 'SELECT * FROM responses'
    c = conn.cursor()
    c.execute(sql)
    for l in c.fetchall():
        print(l)


def getPathNames():
    sql = 'SELECT path FROM paths'
    
    paths = [row[0] for row in conn.execute(sql)]

    return paths


def getPathCount():
    sql = 'SELECT COUNT(*) FROM paths'

    return conn.execute(sql).fetchone()[0]


def getOperationNames():
    sql = '''
        SELECT parameters.method, paths.path
        FROM parameters JOIN paths ON parameters.path_id = paths.id 
        GROUP BY parameters.method, paths.path
        '''

    return conn.execute(sql).fetchall()


def getOperationCount():
    sql = '''
        SELECT COUNT(*) 
        FROM
            (SELECT 1 FROM parameters GROUP BY method, path_id)
         '''

    return conn.execute(sql).fetchone()[0]


def getStatusCodes():
    sql = '''
        SELECT p.path, r.method, r.status
        FROM responses AS r JOIN paths AS p ON r.path_id = p.id
        GROUP BY p.path, r.method, r.status
        '''

    return conn.execute(sql).fetchall()


# NOT WORKING AS EXPECTED.
# It also counts response status not expected in the specification
# It counts the status codes produced by the API during testing
def getStatusCount():
    sql = '''
        SELECT COUNT(*)
        FROM
            (SELECT 1 FROM responses GROUP BY path_id, method, status)
        '''

    return conn.execute(sql).fetchone()[0]


def getResponseTypes():
    sql = '''
        SELECT p.path, r.method, r.content_type
        FROM responses AS r JOIN paths AS p ON r.path_id = p.id
        GROUP BY p.path, r.method, r.content_type
        '''

    return conn.execute(sql).fetchall()

# NOT WORKING.
# It also counts response types not expected in the specification
# It counts the types produced by the API during testing
def getResponseTypesCount():
    sql = '''
        SELECT COUNT(*) 
        FROM 
            (SELECT DISTINCT path_id, method, content_type FROM responses)
        '''
    return conn.execute(sql).fetchone()[0]


def getRequestTypes():
    sql = '''
        SELECT p.path, v.method, v.value
        FROM paths AS p JOIN
            (SELECT p.path_id AS path_id, p.method AS method, v.value AS value
            FROM pvalues AS v JOIN 
                (SELECT *
                FROM parameters
                WHERE name = "Content-Type" AND method IN ("post", "put", "patch", "delete"))
                AS p ON v.param_id = p.id)
            AS v ON p.id = v.path_id
        '''

    return conn.execute(sql).fetchall()


def getRequestTypesCount():
    sql = '''
        SELECT COUNT(*)
        FROM pvalues AS v JOIN 
            (SELECT *
            FROM parameters
            WHERE name = "Content-Type" AND method IN ("post", "put", "patch", "delete"))
            AS p ON v.param_id = p.id
        '''

    return conn.execute(sql).fetchone()[0]


def getParameters():
    sql = '''
        SELECT pt.path, pm.method, pm.name
        FROM parameters AS pm JOIN paths AS pt ON pm.path_id = pt.id
        '''

    return conn.execute(sql).fetchall()


# Headers are counted as params. The following count is wrong due to use of
# unexpected not considered in the specification.
def getParametersCount():
    sql = 'SELECT COUNT(*) FROM parameters'

    return conn.execute(sql).fetchone()[0]

# Used to retrieve path id for parameter value coverage
def getPathIDByName(path):

    sql = 'SELECT id FROM paths WHERE path = ?'
    
    try:
        res = conn.execute(sql, (path,)).fetchone()[0]
        return res

    except TypeError:
        return None


def getParameterValues(path_id, method, paramName):

    sql = '''
        SELECT v.value
        FROM pvalues AS v JOIN
            (SELECT id FROM parameters WHERE path_id = ? AND method = ? AND name = ?)
        AS p ON p.id = v.param_id
        '''

    res = conn.execute(sql, (path_id, method, paramName)).fetchall()
    res = [x[0] for x in res]

    return res

def getOperationTested():
    sql = '''
        SELECT DISTINCT res.path, res.method
        FROM (responses JOIN paths ON responses.path_id=paths.id) AS res
        WHERE CAST(res.status AS integer) >= 200 AND CAST(res.status AS integer) < 300
        '''

    return conn.execute(sql).fetchall()

def getAllErrors():
    sql = '''
        SELECT DISTINCT res.status, res.path, res.body
        FROM (responses JOIN paths ON responses.path_id = paths.id) AS res      
        WHERE CAST(res.status AS int) > 499
        '''

    return conn.execute(sql).fetchall()

def getAllResponseStatusCode():
    sql = '''
        SELECT status
        FROM responses    
        '''

    return conn.execute(sql).fetchall()