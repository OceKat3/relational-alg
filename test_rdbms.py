from rdbms import Recognizer, Parser, tokenizer, sql_grammar, SqlTreeReducer, MockDatabaseSchemaOnly, ExecutionContext, Table, InMemoryDatabase

from pprint import pformat, pprint
from contextlib import contextmanager
# testing utils
def assert_equal(actual, expected):
    assert actual == expected, f'{pformat(actual)} \nwas not equal to \n{pformat(expected)}'

ABC_DATABASE_SCHEMA = MockDatabaseSchemaOnly.from_tables(
    A=[
        ("a", int),
        ("b", ("varchar", 64)), 
    ],
    B=[
        ("c", int)
    ]
)


COMPANY_DATABASE_SCHEMA = MockDatabaseSchemaOnly.from_tables(
    employees=[
        ("eid", int),
        ("managerid", int),
        ("name", ("varchar", 64)), 
    ],
    employee_departments=[
        ("eid", int),
        ("did", ("varchar",10))
    ],
    departments=[
        ("did", ("varchar", 10)),
        ("deptname", ("varchar", 128)),
    ]
)

@contextmanager
def expect_failure(*errors: type[BaseException]):
    
    try :
        yield
    except errors :
        pass
    except BaseException as e :
        raise AssertionError(f"block raised an unexpected error: ", e)
    else:
        raise AssertionError(f"block did not raise any errors, was expecting one of: {errors}")

##

def ast(document):
    tokens = list(tokenizer(document))

    r = Recognizer(document=tokens, real_string_input=document, grammar=sql_grammar)
    r.earley_recognize()

    p = Parser(items=r.state_sets, document=tokens)
    parsetree = p.create_tree()

    return SqlTreeReducer.ast(parsetree)

def test_parse_translate_select_1():
    test_cases = [
        "SELECT 1 as n",
        "SELECT 1 as n;",
        "SELECT 1 as n; SELECT 1 as n",
        "SELECT 1 as n; SELECT 1 as n;",

        "SELECT * FROM Emp as e, Dept as d WHERE e.did = d.did;"
        "SELECT did, COUNT(*) AS n, AVG(salary) AS avg_sal FROM Emp WHERE age > 25 GROUP BY did HAVING COUNT(*) > 5 ORDER BY n DESC LIMIT 10;",
        "SELECT city FROM Emp UNION SELECT city FROM Dept",
        "SELECT t.did, t.n FROM (SELECT did, COUNT(*) AS n FROM Emp GROUP BY did) AS t WHERE t.n > 3;",
        "SELECT a e.d a.b+c.d-(-e.f) AS big_expr g AS f h FROM sometable JOIN someothertable ON d=h LEFT JOIN (select a,b FROM c WHERE d=e) AS asdasd ON a=d GROUP BY a b HAVING c=d",

        "SELECT COUNT(A) AS count_a FROM B;",
        "SELECT a+b as s FROM B GROUP BY a;",
        "SELECT COUNT(a) AS count_a FROM B",
        "SELECT COUNT(a) AS count_a FROM B GROUP BY a;",
        "SELECT COUNT(a) AS count_a FROM B GROUP BY a;",
        "SELECT a FROM B;",
        "SELECT COUNT(a) AS count_a FROM B GROUP BY b;",
        "SELECT b FROM B GROUP BY b;",
        "SELECT a FROM B GROUP BY b;",
    ]

    for document in test_cases:
        print(document)
        assert ast(document) is not None

def test_invalid_parses():
    test_cases = [
        "SELECT 1",
        "SELECT a+b FROM A",
        "SELECT a;;",
        "CREATE TABLE t",
        "SELECT COUNT(*) FROM B",
    ]

    for document in test_cases:
        print(document)
        with expect_failure(SyntaxError) :
            ast(document)
    

def test_typecheck_select_1():
    document = "SELECT 1 AS n"
    sql = ast(document)
    assert sql
    with ExecutionContext.cur_database.set(ABC_DATABASE_SCHEMA) :
        assert_equal(
            sql.typecheck(), 
            [Table.ColDef("n", int)]
        )

def test_typecheck_select_2():
    document = "SELECT a, b FROM A"
    sql = ast(document)
    assert sql
    with ExecutionContext.cur_database.set(ABC_DATABASE_SCHEMA) :
        assert_equal(
            sql.typecheck(), 
            [Table.ColDef("a", int), Table.ColDef("b", ("varchar", 64))]
        )

def test_typecheck_select_3():
    document = "SELECT a AS c FROM A UNION ALL SELECT c FROM B WHERE c>0;"
    sql = ast(document)
    assert sql
    with ExecutionContext.cur_database.set(ABC_DATABASE_SCHEMA) :
        assert_equal(
            sql.typecheck(), 
            [Table.ColDef("c", int)]
        )

def test_typecheck_select_4():
    document = "SELECT b FROM A WHERE a>0 GROUP BY A.b"
    sql = ast(document)
    assert sql
    with ExecutionContext.cur_database.set(ABC_DATABASE_SCHEMA) :
        assert_equal(
            sql.typecheck(), 
            [Table.ColDef("b", ("varchar", 64))]
        )

def test_typecheck_aggregation():
    valid = [
        "SELECT b FROM A WHERE a>0 GROUP BY A.b",
        "SELECT MAX(b) as m AGGREGATE FROM A WHERE a>0",
        "SELECT 1+MAX(a)-MIN(a) as range AGGREGATE FROM A",
        "SELECT DISTINCT COUNT(*) as n AGGREGATE FROM A"
    ]
    syntaxerror = [
        "SELECT b AGGREGATE FROM A GROUP BY b"
    ]
    typeerror = [
        "SELECT b AGGREGATE FROM A",
        "SELECT MAX(MAX(b)) as m AGGREGATE FROM A",
        "SELECT a FROM A GROUP BY b",
        "SELECT MAX(a) as m FROM A"
    ]
    for document in valid:
        print(document)
        sql = ast(document)
        assert sql
        with ExecutionContext.cur_database.set(ABC_DATABASE_SCHEMA) :
            sql.typecheck()
    for document in syntaxerror:
        with expect_failure(SyntaxError):
            sql = ast(document)
    for document in typeerror:
        sql = ast(document)
        assert sql
        with ExecutionContext.cur_database.set(ABC_DATABASE_SCHEMA) :
            with expect_failure(TypeError):
                sql.typecheck()

def test_typecheck_joins():
    valid = [
        "SELECT employees.eid, departments.did FROM employees, employee_departments, departments",
        "SELECT eid, did FROM employees, employee_departments, departments",
        "SELECT employees.name, managers.name AS manager_name FROM employees INNER JOIN employees AS managers ON employees.managerid = managers.eid"
    ]
    syntaxerror = [
        "SELECT * FROM (SELECT * from departments)"
    ]
    typeerror = [
        "SELECT name FROM employees, employees",
        "SELECT employees.name, managers.name FROM employees INNER JOIN employees AS managers ON employees.managerid = managers.eid"
    ]
    for document in valid:
        print(document)
        sql = ast(document)
        assert sql
        with ExecutionContext.cur_database.set(COMPANY_DATABASE_SCHEMA) :
            sql.typecheck()
    for document in syntaxerror:
        with expect_failure(SyntaxError):
            sql = ast(document)
    for document in typeerror:
        sql = ast(document)
        assert sql
        with ExecutionContext.cur_database.set(COMPANY_DATABASE_SCHEMA) :
            with expect_failure(TypeError):
                sql.typecheck()
            

def test_parse_create_table_1():
    test_cases = [
        "CREATE TABLE employees (id NUM name VARCHAR password VARCHAR(64))",
        "CREATE TABLE employees (id NUM, name VARCHAR, password VARCHAR(64))",
    ]

    for document in test_cases:
        assert ast(document) is not None

def test_typecheck_create_table_1():
    test_cases = [
        "CREATE TABLE employees (id NUM name VARCHAR password VARCHAR(64))",
        "CREATE TABLE employees (id NUM, name VARCHAR, password VARCHAR(64))",
    ]
    
    for document in test_cases:
        with ExecutionContext.cur_database.set(MockDatabaseSchemaOnly.from_tables()) :
            sql = ast(document)
            assert sql is not None
            sql.typecheck()
        with expect_failure(TypeError):
            with ExecutionContext.cur_database.set(COMPANY_DATABASE_SCHEMA) :
                sql = ast(document)
                assert sql is not None
                sql.typecheck()

def test_parse_insert_1():
    test_cases = [   
        'INSERT INTO employees VALUES (1, 2, 3), ("A", "B", "asdasdasdasdasd"), (1,2,3,4,5,6,7,8,9)'
    ]

    for document in test_cases:
        assert ast(document) is not None

def test_typecheck_insert_into_1():
    test_cases = [
        'INSERT INTO employees (eid, managerid, name) VALUES (1 2 "asd") (2 3 "sadasdasdasdasd")',
        'INSERT INTO employees (eid, managerid, name) VALUES (1, 2, "asd"), (2,3,"sadasdasdasdasd")',
        'INSERT INTO employees (managerid, eid, name) VALUES (1 2 "asd") (2 3 "sadasdasdasdasd")',
        'INSERT INTO employees (name, managerid, eid) VALUES ("asd", 2, 1)',
        'INSERT INTO employees VALUES (1 2 "asd") (2 3 "sadasdasdasdasd")',
        'INSERT INTO employees VALUES (1, 2, "asd"), (2,3,"sadasdasdasdasd")',
    ]
    
    for document in test_cases:
        with expect_failure(TypeError):
            with ExecutionContext.cur_database.set(MockDatabaseSchemaOnly.from_tables()) :
                sql = ast(document)
                assert sql is not None
                sql.typecheck()
        
        with ExecutionContext.cur_database.set(COMPANY_DATABASE_SCHEMA) :
            sql = ast(document)
            assert sql is not None
            sql.typecheck()

def test_typecheck_insert_into_2():
    typeerrors = [
        'INSERT INTO employees (eid, eid, name) VALUES (1 2 "asd") (2 3 "sadasdasdasdasd")',
        'INSERT INTO employees (eid, name) VALUES (1, 2, "asd"), (2,3,"sadasdasdasdasd")',
        'INSERT INTO employees (eid, name, managerid, asdasd) VALUES (1, 2, "asd"), (2,3,"sadasdasdasdasd")',
        'INSERT INTO employees (name, eid, managerid) VALUES (1, 2, "asd"), (2,3,"sadasdasdasdasd")',
        'INSERT INTO employees VALUES ("a" 2 "asd") (2 3 "sadasdasdasdasd")',
        'INSERT INTO employees VALUES (1, 2, "asd"), (2,"a","sadasdasdasdasd")',
        'INSERT INTO employees (eid, managerid, name) VALUES (1 2 "asd" 3) (2 3 "sadasdasdasdasd" 4 5)',
        'INSERT INTO employees (name, managerid, eid) VALUES (1, 2, "asd"), (2,3,"sadasdasdasdasd")',
    ]   
    
    for document in typeerrors:
        with expect_failure(TypeError):
            with ExecutionContext.cur_database.set(COMPANY_DATABASE_SCHEMA) :
                print(document)
                sql = ast(document)
                assert sql is not None
                sql.typecheck()




def test_memory_db_1():

    db = InMemoryDatabase()

    employees = COMPANY_DATABASE_SCHEMA.get_table_by_name('employees')
    assert employees

    serializer = db.get_tuple_serializer(employees.schema)
    deserializer = db.get_tuple_deserializer(employees.schema)

    assert_equal(len(serializer((1,2,"a"))), 4+4+2+1)

    for tup in [(1,2,"a"), (100,400,"c")]:
        assert_equal(
            deserializer(serializer(tup)),
            tup
        )



"SELECT COUNT(a) FROM B" # this should fail because a is not aggregated
"SELECT COUNT(a) FROM B GROUP BY a;" # this should fail because expressions values need to be renamed
"SELECT COUNT(a) AS count_a FROM B GROUP BY a;" # this should fail because a is aggregated twice
"SELECT a FROM B;" # this should work just fine
"SELECT COUNT(a) FROM B GROUP BY b;" # this should work just fine
"SELECT b FROM B GROUP BY b;" # this should work just fine
"SELECT a FROM B GROUP BY b;" # this should fail because a is not aggregated


"SELECT a FROM B JOIN B ON b1=b2" #should fail typecheck due to an ambiguous self join


from rdbms import Filesystem, InMemoryFilesystem, OnDiskFileystem, BLOCK_SIZE

def _test_filesystem(fs:Filesystem):

    with expect_failure(FileNotFoundError):
        fs.open('a', create_new_file=False)
        
    file = fs.open('a', create_new_file=True)
    
    assert_equal(file.read_block(0), bytearray())
    
    import secrets

    # data = secrets.token_bytes(BLOCK_SIZE)
    data = b'1' * BLOCK_SIZE
    file.write_block(0, data)
    assert_equal(file.read_block(0), data)
    
    # data2 = secrets.token_bytes(BLOCK_SIZE)
    data2 = b'2' * BLOCK_SIZE
    file.write_block(100, data2)
    assert_equal(file.read_block(1), data2)

    file.write_block(0, data2)

    print(file.read_block(0) + file.read_block(1) + file.read_block(2))

    assert_equal(file.read_block(0), data2)

    with expect_failure(ValueError):
        file.write_block(2, b'asdfiuuhasdfiuhasfediuh')

def test_memory_fs():
    mfs = InMemoryFilesystem()
    _test_filesystem(mfs)

def test_disk_fs():
    dfs = OnDiskFileystem(directory="test_data/")
    dfs.clean_directory()
    _test_filesystem(dfs)

import os
def test_disk_filesystem_creates_directory():

    DIR = "asdasdasdasdasdas"

    try :
        os.rmdir(DIR)
    except: pass

    OnDiskFileystem(directory=DIR).open('catalog', create_new_file=True)

    os.stat(DIR)

    try :
        os.rmdir(DIR)
    except: pass
    




# test runner

all_tests = [(key, value) for key, value in locals().items() if key.startswith('test')]

for name, t in all_tests :
    try:
        t()
        print(f'test passed: {name}')
    except BaseException as e:
        print(f'(!) test failed: {name}')
        print(type(e), e)
        raise e